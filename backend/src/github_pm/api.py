from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
import re
import time
from typing import Annotated, Any, AsyncGenerator
from urllib.parse import quote_plus

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
import requests

from github_pm.context import context
from github_pm.issue_hierarchy import (
    apply_graphql_hierarchy,
    build_issue_forest,
    collect_descendant_numbers,
    is_ancestor,
    ISSUE_HIERARCHY_GRAPHQL,
    PARENT_ONLY_GRAPHQL,
)
from github_pm.logger import logger

api_router = APIRouter()


# We sort "semver" style milestones first, then others alphabetically
VERSION_MATCH = re.compile(r"^v\d+\.\d+\.\d+$")

# Bounded retries for transient GitHub gateway timeouts (504).
_GITHUB_504_MAX_ATTEMPTS = 5
_GITHUB_504_BACKOFF_SEC = 1.5

# full+json returns raw markdown ``body`` and rendered ``body_html``.
# html+json alone omits ``body``, which breaks edit-in-place flows.
# Assisted-by: Cursor
_GITHUB_BODY_ACCEPT = {"Accept": "application/vnd.github.full+json"}


class Connector:
    def __init__(self, github_token: str, *, github_repo: str | None = None):
        """Initialize a GitHub connection.

        Args:
            github_token: The GitHub Personal Access Token to use
            github_repo: ``owner/name``; defaults to ``context.github_repo`` when omitted.
        """
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        repo = github_repo if github_repo is not None else context.github_repo
        self.owner, self.repo = repo.split("/", maxsplit=1)
        self.github = requests.session()
        self.github.headers.update(
            {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "Project-Manager",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        logger.info(
            "Initializing GitHub Connector service to %s/%s",
            self.base_url,
            repo,
        )

    def _with_504_retry(
        self, request: Callable[[], requests.Response]
    ) -> requests.Response:
        """Perform one HTTP call, retrying on 504 with a short capped backoff."""
        for attempt in range(_GITHUB_504_MAX_ATTEMPTS):
            response = request()
            if response.status_code == 504 and attempt < _GITHUB_504_MAX_ATTEMPTS - 1:
                delay = _GITHUB_504_BACKOFF_SEC * (attempt + 1)
                logger.warning(
                    "GitHub API 504 Gateway Timeout; waiting %.1fs before retry %d/%d",
                    delay,
                    attempt + 2,
                    _GITHUB_504_MAX_ATTEMPTS,
                )
                time.sleep(delay)
                continue
            response.raise_for_status()
            self.response = response
            return response

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        response = self._with_504_retry(
            lambda: self.github.get(f"{self.base_url}{path}", headers=headers)
        )
        return response.json()

    def get_paged(self, path: str, headers: dict[str, str] | None = None) -> list[dict]:
        url: str | None = f"{self.base_url}{path}"
        results = []
        while url:
            response = self._with_504_retry(
                lambda u=url: self.github.get(u, headers=headers)
            )
            data = response.json()
            logger.debug(f"{url}: {len(data)}")
            results.extend(data)
            url = None
            if response.headers.get("link"):
                links = response.headers.get("link")
                for link in links.split(","):
                    if 'rel="next"' in link:
                        url = link.split(";")[0].strip().strip("<>")
                        logger.debug(f"paging to: {url}")
                        break
        return results

    def search_issue_items(
        self, search_query: str, headers: dict[str, str] | None = None
    ) -> list[dict]:
        """Run ``GET /search/issues`` with pagination; returns the ``items`` array union."""
        q_param = quote_plus(search_query)
        url: str | None = f"{self.base_url}/search/issues?q={q_param}&per_page=100"
        results: list[dict] = []
        while url:
            response = self._with_504_retry(
                lambda u=url: self.github.get(u, headers=headers)
            )
            data = response.json()
            items = data.get("items")
            if isinstance(items, list):
                results.extend(items)
            url = None
            link_header = response.headers.get("link")
            if link_header:
                for link in link_header.split(","):
                    if 'rel="next"' in link:
                        url = link.split(";")[0].strip().strip("<>")
                        logger.debug("search/issues paging to: %s", url)
                        break
        return results

    def patch(
        self, path: str, data: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict:
        response = self._with_504_retry(
            lambda: self.github.patch(
                f"{self.base_url}{path}", json=data, headers=headers
            )
        )
        return response.json()

    def post(
        self, path: str, data: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict:
        response = self._with_504_retry(
            lambda: self.github.post(
                f"{self.base_url}{path}", json=data, headers=headers
            )
        )
        return response.json()

    def post_text(
        self, path: str, text: str, headers: dict[str, str] | None = None
    ) -> str:
        """POST plain text (e.g. ``/markdown/raw``); returns response body as text.

        Generated-by: Cursor
        """
        request_headers = {"Content-Type": "text/plain; charset=utf-8"}
        if headers:
            request_headers.update(headers)
        response = self._with_504_retry(
            lambda: self.github.post(
                f"{self.base_url}{path}",
                data=text.encode("utf-8"),
                headers=request_headers,
            )
        )
        return response.text

    def delete(
        self,
        path: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict:
        response = self._with_504_retry(
            lambda: self.github.delete(
                f"{self.base_url}{path}", json=data, headers=headers
            )
        )
        return response.json() if response.content else {}


async def connection() -> AsyncGenerator[Connector]:
    """FastAPI Dependency to open & close Github connections"""
    connector = None
    try:
        connector = Connector(github_token=context.github_token)
    except Exception as e:
        logger.exception(f"Error opening GitHub service: {e}")
        raise HTTPException(
            status_code=400, detail=f"Can't open GitHub connection: {str(e)!r}"
        )
    try:
        start = time.time()
        yield connector
        logger.debug(f"Elapsed time: {time.time() - start:.3f} seconds")
    except Exception as e:
        logger.exception(f"GitHub error: {str(e)!r}")
        raise HTTPException(
            status_code=400, detail=f"Can't open repository: {str(e)!r}"
        )


@api_router.get("/project")
async def get_project():
    return {
        "app_name": context.app_name,
        "github_repo": context.github_repo,
    }


def _sort_items_by_labels(items: list[dict], sort_by: list[str]) -> list[dict]:
    """Sort open items by label priority, then by number within each bucket.

    Assisted-by: Cursor
    """
    buckets: dict[str, list] = defaultdict(list)
    for item in items:
        labels = {label["name"].lower() for label in item["labels"]}
        for label in sort_by:
            if label in labels:
                buckets[label].append(item)
                break
        else:
            buckets["other"].append(item)
    ordered: list[dict] = []
    for label in sort_by + ["other"]:
        ordered.extend(sorted(buckets[label], key=lambda x: x["number"]))
    return ordered


@api_router.get("/issues/{milestone_number}")
async def get_issues(
    gitctx: Annotated[Connector, Depends(connection)],
    milestone_number: Annotated[int, Path(title="Milestone")],
    sort: Annotated[
        str | None, Query(title="Sort", description="List of labels to sort by")
    ] = None,
):
    """Return open issues (as a sub-issue forest) and PRs for a milestone.

    Issues are nested via GitHub parent/sub-issue links discovered over GraphQL.
    Pull requests remain a flat list. Each sibling list is sorted by optional
    label criteria.
    Assisted-by: Cursor
    """
    if sort:
        sort_by = [s.strip() for s in sort.split(",")]
    else:
        sort_by = []
    start = time.time()
    milestone = "none" if milestone_number == 0 else milestone_number
    raw_items = gitctx.get_paged(
        f"/repos/{context.github_repo}/issues?milestone={milestone}&state=open",
        headers=_GITHUB_BODY_ACCEPT,
    )
    issues: list[dict] = []
    pull_requests: list[dict] = []
    for i in raw_items:
        if "pull_request" in i:
            pull_requests.append(i)
            continue
        try:
            response = gitctx.post(
                "/graphql",
                data={
                    "query": ISSUE_HIERARCHY_GRAPHQL,
                    "variables": {
                        "owner": gitctx.owner,
                        "repo": gitctx.repo,
                        "issue": i["number"],
                    },
                },
            )
            data = response["data"]
            issue_node = data["repository"]["issue"]
            closed_refs = issue_node.get("closedByPullRequestsReferences") or {}
            closed = closed_refs.get("nodes") or []
            if len(closed) > 0:
                i["closed_by"] = [
                    {
                        "number": linked["number"],
                        "title": linked["title"],
                        "url": linked["url"],
                    }
                    for linked in closed
                ]
            apply_graphql_hierarchy(i, issue_node)
        except Exception as e:
            logger.exception(
                f"Error enriching hierarchy/PRs for issue {i['number']}: {e!r}"
            )
            continue
        issues.append(i)
    forest = build_issue_forest(issues, sort_by, _sort_items_by_labels)
    sorted_prs = _sort_items_by_labels(pull_requests, sort_by)
    logger.debug(
        "%s(%s issues, %s PRs) items: %.3f seconds",
        len(raw_items),
        len(forest),
        len(sorted_prs),
        time.time() - start,
    )
    return {"issues": forest, "pull_requests": sorted_prs}


@api_router.get("/issue/{issue_number}")
async def get_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
):
    issue = gitctx.get(
        f"/repos/{context.github_repo}/issues/{issue_number}",
        headers=_GITHUB_BODY_ACCEPT,
    )
    if "pull_request" not in issue:
        query = """query($owner: String!, $repo: String!, $issue: Int!) {
            repository(owner: $owner, name: $repo, followRenames: true) {
                issue(number: $issue) {
                    closedByPullRequestsReferences(first: 100, includeClosedPrs: true) {
                        nodes {
                            number
                            title
                            url
                        }
                    }
                }
            }
        }
        """
        try:
            response = gitctx.post(
                "/graphql",
                data={
                    "query": query,
                    "variables": {
                        "owner": gitctx.owner,
                        "repo": gitctx.repo,
                        "issue": issue["number"],
                    },
                },
            )
            data = response["data"]
            issue_node = data["repository"]["issue"]
            closed = issue_node["closedByPullRequestsReferences"]["nodes"]
            if len(closed) > 0:
                issue["closed_by"] = [
                    {
                        "number": linked["number"],
                        "title": linked["title"],
                        "url": linked["url"],
                    }
                    for linked in closed
                ]
        except Exception as e:
            logger.exception(
                f"Error finding linked PRs for issue {issue['number']}: {e!r}"
            )
    return issue


@api_router.get("/comments/{issue_number}")
async def get_comments(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
):
    start = time.time()
    comments = gitctx.get_paged(
        f"/repos/{context.github_repo}/issues/{issue_number}/comments",
        headers=_GITHUB_BODY_ACCEPT,
    )
    logger.debug(
        f"{len(comments)} issue {issue_number} comments: {time.time() - start:.3f} seconds"
    )
    return comments


class CreateComment(BaseModel):
    """Body for creating an issue comment.

    Generated-by: Cursor
    """

    body: str = Field(title="Comment Body", min_length=1)


@api_router.post("/comments/{issue_number}")
async def create_comment(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    comment: Annotated[CreateComment, Body(title="Comment")],
):
    """Create a comment on an issue.

    Generated-by: Cursor
    """
    created = gitctx.post(
        f"/repos/{context.github_repo}/issues/{issue_number}/comments",
        data={"body": comment.body},
        headers=_GITHUB_BODY_ACCEPT,
    )
    logger.info("Created comment on issue #%s", issue_number)
    return created


class UpdateComment(BaseModel):
    """Body for updating an issue comment.

    Generated-by: Cursor
    """

    body: str = Field(title="Comment Body", min_length=1)


@api_router.patch("/comments/{comment_id}/body")
async def update_comment(
    gitctx: Annotated[Connector, Depends(connection)],
    comment_id: Annotated[int, Path(title="Comment ID")],
    comment: Annotated[UpdateComment, Body(title="Comment")],
):
    """Update an issue comment's markdown body.

    Generated-by: Cursor
    """
    updated = gitctx.patch(
        f"/repos/{context.github_repo}/issues/comments/{comment_id}",
        data={"body": comment.body},
        headers=_GITHUB_BODY_ACCEPT,
    )
    logger.info("Updated comment %s", comment_id)
    return updated


class UpdateIssueBody(BaseModel):
    """Body for updating an issue description.

    Generated-by: Cursor
    """

    body: str = Field(title="Issue Body", default="")


@api_router.patch("/issues/{issue_number}/body")
async def update_issue_body(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    payload: Annotated[UpdateIssueBody, Body(title="Issue Body")],
):
    """Update an issue's markdown description.

    Generated-by: Cursor
    """
    updated = gitctx.patch(
        f"/repos/{context.github_repo}/issues/{issue_number}",
        data={"body": payload.body},
        headers=_GITHUB_BODY_ACCEPT,
    )
    logger.info("Updated body for issue #%s", issue_number)
    return updated


class CloseWithComment(BaseModel):
    """Body for closing an issue with an optional comment.

    Generated-by: Cursor
    """

    body: str = Field(title="Comment Body", min_length=1)


@api_router.post("/issues/{issue_number}/close-with-comment")
async def close_issue_with_comment(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    comment: Annotated[CloseWithComment, Body(title="Comment")],
):
    """Add a comment to an issue and mark it closed.

    Generated-by: Cursor
    """
    created_comment = gitctx.post(
        f"/repos/{context.github_repo}/issues/{issue_number}/comments",
        data={"body": comment.body},
        headers=_GITHUB_BODY_ACCEPT,
    )
    closed_issue = gitctx.patch(
        f"/repos/{context.github_repo}/issues/{issue_number}",
        data={"state": "closed"},
        headers=_GITHUB_BODY_ACCEPT,
    )
    logger.info("Closed issue #%s with comment", issue_number)
    return {"comment": created_comment, "issue": closed_issue}


class RenderMarkdown(BaseModel):
    """Body for rendering markdown via GitHub.

    Generated-by: Cursor
    """

    text: str = Field(title="Markdown Text", default="")


@api_router.post("/markdown")
async def render_markdown(
    gitctx: Annotated[Connector, Depends(connection)],
    payload: Annotated[RenderMarkdown, Body(title="Markdown")],
):
    """Render markdown to HTML using GitHub ``POST /markdown/raw``.

    Generated-by: Cursor
    """
    html = gitctx.post_text("/markdown/raw", payload.text)
    return {"html": html}


class CreateIssue(BaseModel):
    """Body for creating a repository issue (optionally as a sub-issue).

    Generated-by: Cursor
    """

    title: str = Field(title="Issue Title", min_length=1)
    body: str | None = Field(default=None, title="Issue Body")
    labels: list[str] | None = Field(default=None, title="Labels")
    assignees: list[str] | None = Field(default=None, title="Assignees")
    type: str | None = Field(
        default=None,
        title="Issue Type",
        description="GitHub issue type name, e.g. Bug or Feature",
    )
    milestone: int | None = Field(default=None, title="Milestone Number")
    parent_number: int | None = Field(
        default=None,
        title="Parent Issue Number",
        description="When set, link the new issue as a sub-issue of this parent",
    )


@api_router.post("/issues")
async def create_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue: Annotated[CreateIssue, Body(title="Issue")],
):
    """Create an issue; optionally assign milestone and/or parent.

    Generated-by: Cursor
    """
    data: dict[str, Any] = {"title": issue.title}
    if issue.body is not None:
        data["body"] = issue.body
    if issue.labels is not None:
        data["labels"] = issue.labels
    if issue.assignees is not None:
        data["assignees"] = issue.assignees
    if issue.type is not None:
        data["type"] = issue.type
    if issue.milestone is not None and issue.milestone != 0:
        data["milestone"] = issue.milestone

    created = gitctx.post(
        f"/repos/{context.github_repo}/issues",
        data=data,
        headers=_GITHUB_BODY_ACCEPT,
    )
    logger.info("Created issue #%s: %s", created.get("number"), issue.title)

    parent_number = issue.parent_number
    if parent_number is not None:
        if parent_number == created["number"]:
            raise HTTPException(
                status_code=422, detail="An issue cannot be its own parent"
            )
        gitctx.post(
            f"/repos/{context.github_repo}/issues/{parent_number}/sub_issues",
            data={"sub_issue_id": created["id"], "replace_parent": True},
        )
        logger.info(
            "Linked issue #%s as sub-issue of #%s", created["number"], parent_number
        )
        created["parent_number"] = parent_number

    return created


@api_router.get("/issues/{issue_number}/reactions")
async def get_issue_reactions(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
):
    start = time.time()
    reactions = gitctx.get_paged(
        f"/repos/{context.github_repo}/issues/{issue_number}/reactions",
        headers=_GITHUB_BODY_ACCEPT,
    )
    logger.debug(
        f"{len(reactions)} issue {issue_number} reactions: {time.time() - start:.3f} seconds"
    )
    return reactions


@api_router.get("/comments/{comment_id}/reactions")
async def get_comment_reactions(
    gitctx: Annotated[Connector, Depends(connection)],
    comment_id: Annotated[int, Path(title="Comment")],
):
    reactions = gitctx.get_paged(
        f"/repos/{context.github_repo}/issues/comments/{comment_id}/reactions",
        headers=_GITHUB_BODY_ACCEPT,
    )
    return reactions


# """Milestone Management"""


@api_router.get("/milestones")
async def get_milestones(gitctx: Annotated[Connector, Depends(connection)]):
    milestones = gitctx.get_paged(
        f"/repos/{context.github_repo}/milestones",
        headers=_GITHUB_BODY_ACCEPT,
    )
    versions = []
    others = []
    for m in milestones:
        if VERSION_MATCH.match(m["title"]):
            versions.append(m)
        else:
            others.append(m)
    milestones = sorted(versions, key=lambda x: x["title"]) + sorted(
        others, key=lambda x: x["title"]
    )
    milestones.append(
        {
            "title": "none",
            "number": 0,
            "description": "No milestone",
            "due_on": None,
        }
    )
    return milestones


class CreateMilestone(BaseModel):
    title: str = Field(title="Milestone Title")
    description: str | None = Field(default=None, title="Milestone Description")
    due_on: datetime | None = Field(default=None, title="Milestone Due Date")


@api_router.post("/milestones")
async def create_milestone(
    gitctx: Annotated[Connector, Depends(connection)],
    milestone: Annotated[CreateMilestone, Body(title="Milestone")],
):
    logger.info(
        f"Creating milestone: {milestone!r} ({milestone.due_on.isoformat() if milestone.due_on else None!r})"
    )
    data = {
        "title": milestone.title,
        "state": "open",
        "description": milestone.description,
    }
    if milestone.due_on:
        data["due_on"] = milestone.due_on.isoformat()
    m = gitctx.post(f"/repos/{context.github_repo}/milestones", data=data)
    return m


@api_router.delete("/milestones/{milestone_number}")
async def delete_milestone(
    gitctx: Annotated[Connector, Depends(connection)],
    milestone_number: Annotated[int, Path(title="Milestone")],
):
    gitctx.delete(f"/repos/{context.github_repo}/milestones/{milestone_number}")
    return {"message": f"{milestone_number} milestone deleted"}


@api_router.post("/issues/{issue_number}/milestone/{milestone_number}")
async def add_milestone_to_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    milestone_number: Annotated[int, Path(title="Milestone")],
):
    issue = gitctx.patch(
        f"/repos/{context.github_repo}/issues/{issue_number}",
        data={"milestone": milestone_number},
    )
    return issue


@api_router.delete("/issues/{issue_number}/milestone/{milestone_number}")
async def remove_milestone_from_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    milestone_number: Annotated[int, Path(title="Milestone")],
):
    issue = gitctx.patch(
        f"/repos/{context.github_repo}/issues/{issue_number}",
        data={"milestone": None},
    )
    return issue


def _list_sub_issue_numbers(gitctx: Connector, issue_number: int) -> list[int]:
    """List child issue numbers via REST; fall back to empty on failure.

    Generated-by: Cursor
    """
    try:
        items = gitctx.get_paged(
            f"/repos/{context.github_repo}/issues/{issue_number}/sub_issues"
        )
        return [item["number"] for item in items if "number" in item]
    except Exception as e:
        logger.exception("Failed listing sub-issues for #%s: %r", issue_number, e)
        return []


def _cascade_milestone(
    gitctx: Connector,
    root_number: int,
    milestone_number: int | None,
) -> list[int]:
    """Set milestone on root and all GitHub descendants. Returns updated numbers.

    Generated-by: Cursor
    """

    def list_children(n: int) -> list[int]:
        return _list_sub_issue_numbers(gitctx, n)

    numbers = [root_number] + collect_descendant_numbers(list_children, root_number)
    updated: list[int] = []
    for number in numbers:
        gitctx.patch(
            f"/repos/{context.github_repo}/issues/{number}",
            data={"milestone": milestone_number},
        )
        updated.append(number)
    return updated


def _graphql_issue_node(gitctx: Connector, issue_number: int) -> dict:
    response = gitctx.post(
        "/graphql",
        data={
            "query": PARENT_ONLY_GRAPHQL,
            "variables": {
                "owner": gitctx.owner,
                "repo": gitctx.repo,
                "issue": issue_number,
            },
        },
    )
    data = response.get("data") or {}
    repo = data.get("repository") or {}
    issue_node = repo.get("issue")
    if not issue_node:
        raise HTTPException(status_code=404, detail=f"Issue #{issue_number} not found")
    return issue_node


class SetIssueParent(BaseModel):
    parent_number: int = Field(title="Parent Issue Number")


@api_router.put("/issues/{issue_number}/parent")
async def set_issue_parent(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    body: Annotated[SetIssueParent, Body(title="Parent")],
):
    """Link issue as a sub-issue of parent, cascading milestone when needed.

    Generated-by: Cursor
    """
    parent_number = body.parent_number
    if parent_number == issue_number:
        raise HTTPException(status_code=422, detail="An issue cannot be its own parent")

    def list_children(n: int) -> list[int]:
        return _list_sub_issue_numbers(gitctx, n)

    if is_ancestor(list_children, issue_number, parent_number):
        raise HTTPException(
            status_code=422,
            detail="Cannot link an issue under one of its descendants",
        )

    child = gitctx.get(f"/repos/{context.github_repo}/issues/{issue_number}")
    parent = gitctx.get(f"/repos/{context.github_repo}/issues/{parent_number}")

    gitctx.post(
        f"/repos/{context.github_repo}/issues/{parent_number}/sub_issues",
        data={"sub_issue_id": child["id"], "replace_parent": True},
    )

    child_ms = (child.get("milestone") or {}).get("number")
    parent_ms = (parent.get("milestone") or {}).get("number")
    updated_issue_numbers: list[int] = []
    if child_ms != parent_ms:
        # parent_ms may be None (no milestone); still cascade to match parent.
        updated_issue_numbers = _cascade_milestone(gitctx, issue_number, parent_ms)

    return {
        "issue_number": issue_number,
        "parent_number": parent_number,
        "from_milestone": child_ms,
        "to_milestone": parent_ms,
        "updated_issue_numbers": updated_issue_numbers,
    }


@api_router.delete("/issues/{issue_number}/parent")
async def clear_issue_parent(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
):
    """Unlink issue from its current parent (becomes an epic).

    Generated-by: Cursor
    """
    child = gitctx.get(f"/repos/{context.github_repo}/issues/{issue_number}")
    issue_node = _graphql_issue_node(gitctx, issue_number)
    parent = issue_node.get("parent")
    if not parent or parent.get("number") is None:
        raise HTTPException(
            status_code=404, detail=f"Issue #{issue_number} has no parent"
        )
    parent_number = parent["number"]
    gitctx.delete(
        f"/repos/{context.github_repo}/issues/{parent_number}/sub_issue",
        data={"sub_issue_id": child["id"]},
    )
    return {
        "issue_number": issue_number,
        "parent_number": parent_number,
        "message": "parent cleared",
    }


@api_router.post("/issues/{issue_number}/adopt-parent-milestone")
async def adopt_parent_milestone(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
):
    """Move this issue and descendants to its GitHub parent's milestone.

    Generated-by: Cursor
    """
    issue = gitctx.get(f"/repos/{context.github_repo}/issues/{issue_number}")
    issue_node = _graphql_issue_node(gitctx, issue_number)
    parent = issue_node.get("parent")
    if not parent or parent.get("number") is None:
        raise HTTPException(
            status_code=404, detail=f"Issue #{issue_number} has no parent"
        )
    parent_ms_info = parent.get("milestone")
    if not parent_ms_info or parent_ms_info.get("number") is None:
        raise HTTPException(
            status_code=422,
            detail=f"Parent #{parent['number']} has no milestone to adopt",
        )
    to_milestone = parent_ms_info["number"]
    from_milestone = (issue.get("milestone") or {}).get("number")
    updated = _cascade_milestone(gitctx, issue_number, to_milestone)
    return {
        "issue_number": issue_number,
        "parent_number": parent["number"],
        "from_milestone": from_milestone,
        "to_milestone": to_milestone,
        "updated_issue_numbers": updated,
    }


# """Label Management"""


@api_router.get("/labels")
async def get_labels(gitctx: Annotated[Connector, Depends(connection)]):
    labels = gitctx.get_paged(
        f"/repos/{context.github_repo}/labels",
        headers=_GITHUB_BODY_ACCEPT,
    )
    return labels


class CreateLabel(BaseModel):
    name: str = Field(title="Label Name")
    color: str = Field(title="Label Color")
    description: str | None = Field(default=None, title="Label Description")


@api_router.post("/labels")
async def create_label(
    gitctx: Annotated[Connector, Depends(connection)],
    label: Annotated[CreateLabel, Body(title="Label")],
):
    response = gitctx.post(
        f"/repos/{context.github_repo}/labels",
        data={
            "name": label.name,
            "color": label.color,
            "description": label.description,
        },
    )
    return response


@api_router.delete("/labels/{label_name}")
async def delete_label(
    gitctx: Annotated[Connector, Depends(connection)], label_name: str
):
    gitctx.delete(f"/repos/{context.github_repo}/labels/{label_name}")
    return {"message": f"{label_name} label deleted"}


@api_router.post("/issues/{issue_number}/labels/{label_name}")
async def add_label_to_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    label_name: Annotated[str, Path(title="Label")],
):
    issue = gitctx.get(f"/repos/{context.github_repo}/issues/{issue_number}")
    labels = set([label["name"] for label in issue["labels"]])
    if label_name not in labels:
        labels.add(label_name)
        issue = gitctx.patch(
            f"/repos/{context.github_repo}/issues/{issue_number}",
            data={"labels": list(labels)},
        )
    return issue


@api_router.delete("/issues/{issue_number}/labels/{label_name}")
async def remove_label_from_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    label_name: Annotated[str, Path(title="Label")],
):
    issue = gitctx.get(f"/repos/{context.github_repo}/issues/{issue_number}")
    labels = set([label["name"] for label in issue["labels"]])
    if label_name in labels:
        labels.remove(label_name)
        issue = gitctx.patch(
            f"/repos/{context.github_repo}/issues/{issue_number}",
            data={"labels": list(labels)},
        )
    return issue


# Assignee Management


@api_router.get("/assignees")
async def get_assignees(gitctx: Annotated[Connector, Depends(connection)]):
    """Get all allowed assignees for the repository"""
    assignees = gitctx.get_paged(
        f"/repos/{context.github_repo}/assignees",
        headers=_GITHUB_BODY_ACCEPT,
    )
    return sorted(assignees, key=lambda x: x["login"])


@api_router.post("/issues/{issue_number}/assignees")
async def add_assignee_to_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    assignees: Annotated[list[str], Body(title="Assignees")],
):
    # Use PATCH to replace all assignees (GitHub API best practice)
    issue = gitctx.patch(
        f"/repos/{context.github_repo}/issues/{issue_number}",
        data={"assignees": assignees},
    )
    logger.info(
        f"Added assignees to issue {issue_number}: {[i['login'] for i in issue['assignees']]}"
    )
    return issue


@api_router.delete("/issues/{issue_number}/assignees")
async def remove_assignee_from_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    assignees: Annotated[list[str], Body(title="Assignees")],
):
    issue = gitctx.delete(
        f"/repos/{context.github_repo}/issues/{issue_number}/assignees",
        data={"assignees": assignees},
    )
    logger.info(
        f"Removed assignees from issue {issue_number}: {[i['login'] for i in issue['assignees']]}"
    )
    return issue
