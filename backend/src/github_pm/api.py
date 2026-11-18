"""HTTP routes for Planning. Assisted-by: Codex."""

from collections import defaultdict
from datetime import datetime
import time
from typing import Annotated, Any, AsyncGenerator, Literal, NoReturn
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
import requests

from github_pm import planning_reader as pr
from github_pm.context import context
from github_pm.execution import offload
from github_pm.github_client import Connector
from github_pm.issue_hierarchy import (
    apply_graphql_hierarchy,
    apply_graphql_links,
    build_issue_forest,
)
from github_pm.logger import logger
from github_pm.report_queries import execute
from github_pm.repository_catalog import catalog, VERSION_MATCH

api_router = APIRouter()


# We sort "semver" style milestones first, then others alphabetically


# Assisted-by: openai-code-assist
def _milestone_sort_key(milestone: dict[str, Any]) -> tuple:
    """Sort version milestones numerically before other milestones."""
    title = milestone.get("title") or ""
    version_match = VERSION_MATCH.fullmatch(title)
    if version_match:
        return (
            0,
            tuple(int(part) for part in version_match.group(0)[1:].split(".")),
            "",
        )
    return (1, (), title)


# Raw Markdown and GitHub-rendered HTML are both required by the editors.
_GITHUB_BODY_ACCEPT = {"Accept": "application/vnd.github.full+json"}


def _github_http_error_detail(exc: requests.HTTPError) -> str:
    """Best-effort message from a GitHub REST error response.

    Generated-by: Cursor
    """
    response = exc.response
    if response is None:
        return str(exc)
    try:
        payload = response.json()
    except ValueError:
        return (response.text or str(exc)).strip() or str(exc)
    if isinstance(payload, dict):
        message = payload.get("message")
        errors = payload.get("errors")
        if message and errors:
            return f"{message}: {errors}"
        if message:
            return str(message)
    return (response.text or str(exc)).strip() or str(exc)


def _raise_github_http_error(exc: requests.HTTPError) -> NoReturn:
    """Convert ``requests.HTTPError`` into an ``HTTPException`` with GitHub's status.

    Generated-by: Cursor
    """
    status = 502
    if exc.response is not None:
        status = exc.response.status_code or status
    raise HTTPException(
        status_code=status, detail=_github_http_error_detail(exc)
    ) from exc


async def connection() -> AsyncGenerator[Connector]:
    """FastAPI Dependency to open & close Github connections"""
    connector = None
    try:
        connector = Connector(
            github_token=context.github_token, github_repo=context.github_repo
        )
    except Exception as e:
        logger.exception(f"Error opening GitHub service: {e}")
        raise HTTPException(
            status_code=400, detail=f"Can't open GitHub connection: {str(e)!r}"
        )
    try:
        start = time.time()
        yield connector
        logger.debug(f"Elapsed time: {time.time() - start:.3f} seconds")
    except HTTPException:
        raise
    except requests.HTTPError as e:
        logger.exception(f"GitHub HTTP error: {str(e)!r}")
        _raise_github_http_error(e)
    except Exception as e:
        logger.exception(f"GitHub error: {str(e)!r}")
        raise HTTPException(
            status_code=400, detail=f"Can't open repository: {str(e)!r}"
        )
    finally:
        connector.close()


@api_router.get("/project")
@offload
def get_project():
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
@offload
def get_issues(
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
    issues = [item for item in raw_items if "pull_request" not in item]
    pull_requests = [item for item in raw_items if "pull_request" in item]
    enriched = pr.enrich_issues(gitctx, issues)
    for issue in issues:
        apply_graphql_links(issue, enriched[issue["number"]])
        apply_graphql_hierarchy(issue, enriched[issue["number"]])
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
@offload
def get_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
):
    issue = gitctx.get(
        f"/repos/{context.github_repo}/issues/{issue_number}",
        headers=_GITHUB_BODY_ACCEPT,
    )
    if "pull_request" not in issue:
        node = pr.enrich_issues(gitctx, [issue])[issue["number"]]
        apply_graphql_links(issue, node)
    return issue


@api_router.get("/comments/{issue_number}")
@offload
def get_comments(
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
    return pr.comment_reactions(gitctx, comments)


class CreateComment(BaseModel):
    """Body for creating an issue comment.

    Generated-by: Cursor
    """

    body: str = Field(title="Comment Body", min_length=1)


@api_router.post("/comments/{issue_number}")
@offload
def create_comment(
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
@offload
def update_comment(
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
@offload
def update_issue_body(
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


class UpdateIssueTitle(BaseModel):
    """Body for updating an issue title.

    Assisted-by: openai-code-assist
    """

    title: str = Field(title="Issue Title", min_length=1)


@api_router.patch("/issues/{issue_number}/title")
@offload
def update_issue_title(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    payload: Annotated[UpdateIssueTitle, Body(title="Issue Title")],
):
    """Update an issue's title.

    Assisted-by: openai-code-assist
    """
    updated = gitctx.patch(
        f"/repos/{context.github_repo}/issues/{issue_number}",
        data={"title": payload.title},
        headers=_GITHUB_BODY_ACCEPT,
    )
    logger.info("Updated title for issue #%s", issue_number)
    return updated


# Assisted-by: openai-code-assist
class UpdateIssueType(BaseModel):
    """Body for updating an issue type."""

    type: str = Field(title="Issue Type", min_length=1)


# Assisted-by: openai-code-assist
@api_router.patch("/issues/{issue_number}/type")
@offload
def update_issue_type(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    payload: Annotated[UpdateIssueType, Body(title="Issue Type")],
):
    """Update an issue's GitHub issue type."""
    updated = gitctx.patch(
        f"/repos/{context.github_repo}/issues/{issue_number}",
        data={"type": payload.type},
        headers=_GITHUB_BODY_ACCEPT,
    )
    logger.info("Updated type for issue #%s", issue_number)
    return updated


class CloseIssueRequest(BaseModel):
    """Body for closing an issue with a reason and optional comment.

    Generated-by: Cursor
    """

    reason: Literal["done", "obsolete"] = Field(title="Close Reason", default="done")
    body: str | None = Field(title="Comment Body", default=None)


@api_router.post("/issues/{issue_number}/close-with-comment")
@offload
def close_issue_with_comment(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    comment: Annotated[CloseIssueRequest, Body(title="Comment")],
):
    """Add a comment to an issue and mark it closed.

    Generated-by: Cursor
    """
    resolved_body = (comment.body or "").strip() or (
        "Obsolete" if comment.reason == "obsolete" else "Done"
    )
    state_reason = "not_planned" if comment.reason == "obsolete" else "completed"
    created_comment = gitctx.post(
        f"/repos/{context.github_repo}/issues/{issue_number}/comments",
        data={"body": resolved_body},
        headers=_GITHUB_BODY_ACCEPT,
    )
    closed_issue = gitctx.patch(
        f"/repos/{context.github_repo}/issues/{issue_number}",
        data={"state": "closed", "state_reason": state_reason},
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
@offload
def render_markdown(
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
        description="GitHub issue type name, e.g. Bug, Feature, or Task",
    )
    milestone: int | None = Field(default=None, title="Milestone Number")
    parent_number: int | None = Field(
        default=None,
        title="Parent Issue Number",
        description="When set, link the new issue as a sub-issue of this parent",
    )


@api_router.post("/issues")
@offload
def create_issue(
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
@offload
def get_issue_reactions(
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
@offload
def get_comment_reactions(
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
@offload
def get_milestones(
    gitctx: Annotated[Connector, Depends(connection)],
    state: Annotated[
        Literal["open", "closed"],
        Query(title="Milestone State"),
    ] = "open",
):
    milestones = catalog(gitctx, "milestones", state=state)
    milestones = sorted(milestones, key=_milestone_sort_key)
    if state == "open":
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


# Assisted-by: openai-code-assist
class UpdateMilestone(BaseModel):
    title: str = Field(title="Milestone Title")
    description: str | None = Field(default=None, title="Milestone Description")
    due_on: datetime | None = Field(default=None, title="Milestone Due Date")


# Assisted-by: openai-code-assist
class UpdateMilestoneState(BaseModel):
    state: Literal["open", "closed"] = Field(title="Milestone State")


@api_router.post("/milestones")
@offload
def create_milestone(
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


@api_router.patch("/milestones/{milestone_number}")
@offload
def update_milestone(
    gitctx: Annotated[Connector, Depends(connection)],
    milestone_number: Annotated[int, Path(title="Milestone")],
    milestone: Annotated[UpdateMilestone, Body(title="Milestone")],
):
    data = {
        "title": milestone.title,
        "description": milestone.description,
        "due_on": milestone.due_on.isoformat() if milestone.due_on else None,
    }
    return gitctx.patch(
        f"/repos/{context.github_repo}/milestones/{milestone_number}", data=data
    )


# Assisted-by: openai-code-assist
@api_router.get("/milestones/{milestone_number}/open-counts")
@offload
def get_milestone_open_counts(
    gitctx: Annotated[Connector, Depends(connection)],
    milestone_number: Annotated[int, Path(title="Milestone")],
):
    """Return open issue and pull-request counts for a milestone."""
    data = execute(
        pr._post(gitctx),
        """
query($owner:String!,$repo:String!,$number:Int!) {
  repository(owner:$owner,name:$repo) {
    milestone(number:$number) {
      issues(states:[OPEN],first:1) { totalCount }
      pullRequests(states:[OPEN],first:1) { totalCount }
    }
  }
  rateLimit { cost }
}
""",
        {"owner": gitctx.owner, "repo": gitctx.repo, "number": milestone_number},
    )
    milestone = (data.get("repository") or {}).get("milestone")
    if milestone is None:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return {
        "open_issues": milestone["issues"]["totalCount"],
        "open_pull_requests": milestone["pullRequests"]["totalCount"],
    }


# Assisted-by: openai-code-assist
@api_router.patch("/milestones/{milestone_number}/state")
@offload
def update_milestone_state(
    gitctx: Annotated[Connector, Depends(connection)],
    milestone_number: Annotated[int, Path(title="Milestone")],
    milestone: Annotated[UpdateMilestoneState, Body(title="Milestone State")],
):
    """Open or close a milestone without modifying its other fields."""
    return gitctx.patch(
        f"/repos/{context.github_repo}/milestones/{milestone_number}",
        data={"state": milestone.state},
    )


@api_router.delete("/milestones/{milestone_number}")
@offload
def delete_milestone(
    gitctx: Annotated[Connector, Depends(connection)],
    milestone_number: Annotated[int, Path(title="Milestone")],
):
    gitctx.delete(f"/repos/{context.github_repo}/milestones/{milestone_number}")
    return {"message": f"{milestone_number} milestone deleted"}


@api_router.post("/issues/{issue_number}/milestone/{milestone_number}")
@offload
def add_milestone_to_issue(
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
@offload
def remove_milestone_from_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    milestone_number: Annotated[int, Path(title="Milestone")],
):
    issue = gitctx.patch(
        f"/repos/{context.github_repo}/issues/{issue_number}",
        data={"milestone": None},
    )
    return issue


def _cascade_milestone(
    gitctx: Connector,
    root_number: int,
    milestone_number: int | None,
    descendants: list[int] | None = None,
) -> list[int]:
    """Set milestone on root and all GitHub descendants. Returns updated numbers.

    Generated-by: Cursor
    """

    numbers = [root_number] + (
        pr.descendants(gitctx, root_number) if descendants is None else descendants
    )
    updated: list[int] = []
    for number in numbers:
        try:
            gitctx.patch(
                f"/repos/{context.github_repo}/issues/{number}",
                data={"milestone": milestone_number},
            )
        except Exception as error:
            # GitHub cascades are not transactional; an ambiguous failed write
            # can also have applied. Reload both columns rather than roll back.
            raise HTTPException(
                status_code=502,
                detail={
                    "message": f"Milestone update stopped at issue #{number}: {error}",
                    "updated_issue_numbers": updated,
                    "failed_issue_number": number,
                    "refresh_required": True,
                },
            ) from error
        updated.append(number)
    return updated


def _graphql_issue_node(gitctx: Connector, issue_number: int) -> dict:
    return pr.issue_nodes(
        gitctx, [issue_number], pr.IDENTITY + " " + pr.PARENT, issue_only=True
    )[issue_number]


class SetIssueParent(BaseModel):
    parent_number: int = Field(title="Parent Issue Number")


@api_router.put("/issues/{issue_number}/parent")
@offload
def set_issue_parent(
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

    descendant_numbers = pr.descendants(gitctx, issue_number)
    if parent_number in descendant_numbers:
        raise HTTPException(
            status_code=422, detail="Cannot link an issue under one of its descendants"
        )
    nodes = pr.issue_nodes(gitctx, [issue_number, parent_number], issue_only=True)
    child = pr.rest_identity(nodes[issue_number])
    parent = pr.rest_identity(nodes[parent_number])

    gitctx.post(
        f"/repos/{context.github_repo}/issues/{parent_number}/sub_issues",
        data={"sub_issue_id": child["id"], "replace_parent": True},
    )

    child_ms = (child.get("milestone") or {}).get("number")
    parent_ms = (parent.get("milestone") or {}).get("number")
    updated_issue_numbers: list[int] = []
    if child_ms != parent_ms:
        # parent_ms may be None (no milestone); still cascade to match parent.
        updated_issue_numbers = _cascade_milestone(
            gitctx, issue_number, parent_ms, descendant_numbers
        )

    return {
        "issue_number": issue_number,
        "parent_number": parent_number,
        "from_milestone": child_ms,
        "to_milestone": parent_ms,
        "updated_issue_numbers": updated_issue_numbers,
    }


@api_router.delete("/issues/{issue_number}/parent")
@offload
def clear_issue_parent(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
):
    """Unlink issue from its current parent (becomes an epic).

    Generated-by: Cursor
    """
    issue_node = _graphql_issue_node(gitctx, issue_number)
    child = pr.rest_identity(issue_node)
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
@offload
def adopt_parent_milestone(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
):
    """Move this issue and descendants to its GitHub parent's milestone.

    Generated-by: Cursor
    """
    issue_node = _graphql_issue_node(gitctx, issue_number)
    issue = pr.rest_identity(issue_node)
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


# """Issue dependencies (blocked by / blocking)"""


class AddDependency(BaseModel):
    issue_number: int = Field(title="Related Issue Number")


class AddCloseReference(BaseModel):
    """Request body for adding a pull request as a closing reference.

    Generated-by: openai-code-assist
    """

    pull_request_number: int = Field(title="Pull Request Number")


def _dependency_link_payload(issue: dict) -> dict:
    """Normalize a GitHub REST issue into the Planning dependency shape.

    Generated-by: Cursor
    """
    state = issue.get("state") or ""
    if isinstance(state, str):
        state = state.upper()
    return {
        "id": issue["id"],
        "number": issue["number"],
        "title": issue.get("title"),
        "url": issue.get("html_url") or issue.get("url"),
        "state": state,
    }


def _get_issue_for_dependency(gitctx: Connector, issue_number: int) -> dict:
    """Fetch an issue and reject pull requests / missing targets.

    Generated-by: Cursor
    """
    try:
        issue = gitctx.get(f"/repos/{context.github_repo}/issues/{issue_number}")
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", None)
        if status == 404:
            raise HTTPException(
                status_code=404, detail=f"Issue #{issue_number} not found"
            ) from exc
        raise
    if "pull_request" in issue:
        raise HTTPException(
            status_code=422,
            detail=f"#{issue_number} is a pull request; dependencies require issues",
        )
    return issue


def _dependency_pair(gitctx, first, second):
    nodes = pr.issue_nodes(gitctx, [first, second])
    if any(n["__typename"] != "Issue" for n in nodes.values()):
        raise HTTPException(
            status_code=422, detail="Dependencies require issues, not pull requests"
        )
    return {number: pr.rest_identity(node) for number, node in nodes.items()}


def _close_reference_payload(pull_request: dict) -> dict:
    """Normalize a pull request into the Planning closed-by link shape.

    Generated-by: openai-code-assist
    """
    return {
        "number": pull_request["number"],
        "title": pull_request.get("title"),
        "url": pull_request.get("html_url") or pull_request.get("url"),
    }


def _add_close_reference(gitctx: Connector, issue: dict, pull_request: dict) -> dict:
    """Manually link a pull request as a closing reference for an issue.

    Generated-by: openai-code-assist
    """
    if not issue.get("node_id") or not pull_request.get("node_id"):
        raise HTTPException(
            status_code=502,
            detail="GitHub did not return node IDs for the issue and pull request",
        )
    response = gitctx.post(
        "/graphql",
        data={
            "query": """
mutation($issueId: ID!, $pullRequestIds: [ID!]!) {
  addCloseIssueReferences(
    input: {issueId: $issueId, pullRequestIds: $pullRequestIds}
  ) {
    issue {
      number
    }
  }
}
""",
            "variables": {
                "issueId": issue["node_id"],
                "pullRequestIds": [pull_request["node_id"]],
            },
        },
    )
    errors = response.get("errors") or []
    if errors:
        detail = "; ".join(
            str(error.get("message", error)) if isinstance(error, dict) else str(error)
            for error in errors
        )
        raise HTTPException(status_code=502, detail=detail)
    return _close_reference_payload(pull_request)


@api_router.post("/issues/{issue_number}/close-references")
@offload
def add_close_reference(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    body: Annotated[AddCloseReference, Body(title="Closing Reference")],
):
    """Manually link a pull request as closing this issue.

    Generated-by: openai-code-assist
    """
    nodes = pr.issue_nodes(gitctx, [issue_number, body.pull_request_number])
    issue = pr.rest_identity(nodes[issue_number])
    if "pull_request" in issue:
        raise HTTPException(
            status_code=422,
            detail=(
                f"#{issue_number} is a pull request; "
                "closing references require issues"
            ),
        )
    pull_request = pr.rest_identity(nodes[body.pull_request_number])
    if "pull_request" not in pull_request:
        raise HTTPException(
            status_code=422,
            detail=f"#{body.pull_request_number} is not a pull request",
        )
    linked = _add_close_reference(gitctx, issue, pull_request)
    return {
        "issue_number": issue_number,
        "relationship": "closed_by",
        "linked_pull_request": linked,
    }


def _dependency_already_exists(exc: requests.HTTPError) -> bool:
    """True when GitHub rejects a duplicate blocked-by edge.

    Generated-by: Cursor
    """
    if exc.response is None or exc.response.status_code != 422:
        return False
    detail = _github_http_error_detail(exc).lower()
    return "already been taken" in detail or "already exists" in detail


def _post_blocked_by_dependency(
    gitctx: Connector, blocked_issue_number: int, blocking_issue_id: int
) -> dict:
    """POST a blocked-by edge; return GitHub's body (possibly empty).

    Generated-by: Cursor
    """
    try:
        return gitctx.post(
            f"/repos/{context.github_repo}/issues/{blocked_issue_number}/"
            "dependencies/blocked_by",
            data={"issue_id": blocking_issue_id},
        )
    except requests.HTTPError as exc:
        if _dependency_already_exists(exc):
            return {}
        _raise_github_http_error(exc)


@api_router.post("/issues/{issue_number}/dependencies/blocked_by")
@offload
def add_blocked_by(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    body: Annotated[AddDependency, Body(title="Dependency")],
):
    """Mark this issue as blocked by another issue.

    Generated-by: Cursor
    """
    if body.issue_number == issue_number:
        raise HTTPException(
            status_code=422, detail="An issue cannot be blocked by itself"
        )
    nodes = _dependency_pair(gitctx, issue_number, body.issue_number)
    blocker = nodes[body.issue_number]
    linked = _post_blocked_by_dependency(gitctx, issue_number, blocker["id"])
    return {
        "issue_number": issue_number,
        "relationship": "blocked_by",
        "linked_issue": _dependency_link_payload(linked or blocker),
    }


@api_router.delete(
    "/issues/{issue_number}/dependencies/blocked_by/{blocking_issue_number}"
)
@offload
def remove_blocked_by(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    blocking_issue_number: Annotated[int, Path(title="Blocking Issue Number")],
):
    """Remove a blocked-by dependency from this issue.

    Generated-by: Cursor
    """
    blocker = _get_issue_for_dependency(gitctx, blocking_issue_number)
    try:
        gitctx.delete(
            f"/repos/{context.github_repo}/issues/{issue_number}/dependencies/"
            f"blocked_by/{blocker['id']}"
        )
    except requests.HTTPError as exc:
        _raise_github_http_error(exc)
    return {
        "issue_number": issue_number,
        "relationship": "blocked_by",
        "blocking_issue_number": blocking_issue_number,
        "message": "blocked_by removed",
    }


@api_router.post("/issues/{issue_number}/dependencies/blocking")
@offload
def add_blocking(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    body: Annotated[AddDependency, Body(title="Dependency")],
):
    """Mark this issue as blocking another issue.

    Generated-by: Cursor
    """
    if body.issue_number == issue_number:
        raise HTTPException(status_code=422, detail="An issue cannot block itself")
    nodes = _dependency_pair(gitctx, issue_number, body.issue_number)
    current, blocked = nodes[issue_number], nodes[body.issue_number]
    _post_blocked_by_dependency(gitctx, body.issue_number, current["id"])
    return {
        "issue_number": issue_number,
        "relationship": "blocking",
        "linked_issue": _dependency_link_payload(blocked),
    }


@api_router.delete(
    "/issues/{issue_number}/dependencies/blocking/{blocked_issue_number}"
)
@offload
def remove_blocking(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    blocked_issue_number: Annotated[int, Path(title="Blocked Issue Number")],
):
    """Stop this issue from blocking another issue.

    Generated-by: Cursor
    """
    current = _get_issue_for_dependency(gitctx, issue_number)
    try:
        gitctx.delete(
            f"/repos/{context.github_repo}/issues/{blocked_issue_number}/dependencies/"
            f"blocked_by/{current['id']}"
        )
    except requests.HTTPError as exc:
        _raise_github_http_error(exc)
    return {
        "issue_number": issue_number,
        "relationship": "blocking",
        "blocked_issue_number": blocked_issue_number,
        "message": "blocking removed",
    }


# """Label Management"""


@api_router.get("/labels")
@offload
def get_labels(gitctx: Annotated[Connector, Depends(connection)]):
    return catalog(gitctx, "labels")


class CreateLabel(BaseModel):
    name: str = Field(title="Label Name")
    color: str = Field(title="Label Color")
    description: str | None = Field(default=None, title="Label Description")


class UpdateLabel(BaseModel):
    """Body for updating a repository label.

    Assisted-by: openai-code-assist
    """

    name: str = Field(title="Label Name")
    color: str | None = Field(default=None, title="Label Color")
    description: str | None = Field(default=None, title="Label Description")


@api_router.post("/labels")
@offload
def create_label(
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


@api_router.patch("/labels/{label_name:path}")
@offload
def update_label(
    gitctx: Annotated[Connector, Depends(connection)],
    label_name: str,
    label: Annotated[UpdateLabel, Body(title="Label")],
):
    """Update a repository label, including its name, color, or description.

    Assisted-by: openai-code-assist
    """

    response = gitctx.patch(
        f"/repos/{context.github_repo}/labels/{quote(label_name, safe='')}",
        data={
            "new_name": label.name,
            "color": label.color,
            "description": label.description,
        },
    )
    return response


@api_router.delete("/labels/{label_name:path}")
@offload
def delete_label(gitctx: Annotated[Connector, Depends(connection)], label_name: str):
    gitctx.delete(f"/repos/{context.github_repo}/labels/{quote(label_name, safe='')}")
    return {"message": f"{label_name} label deleted"}


@api_router.post("/issues/{issue_number}/labels/{label_name:path}")
@offload
def add_label_to_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    label_name: Annotated[str, Path(title="Label")],
):
    return {
        "labels": gitctx.post(
            f"/repos/{context.github_repo}/issues/{issue_number}/labels",
            data={"labels": [label_name]},
        )
    }


@api_router.delete("/issues/{issue_number}/labels/{label_name:path}")
@offload
def remove_label_from_issue(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    label_name: Annotated[str, Path(title="Label")],
):
    try:
        labels = gitctx.delete(
            f"/repos/{context.github_repo}/issues/{issue_number}/labels/{quote(label_name, safe='')}"
        )
    except requests.HTTPError as exc:
        if exc.response is None or exc.response.status_code != 404:
            raise
        # An absent label remains a successful no-op, but an inaccessible issue
        # must not be mistaken for one. This exceptional path needs one read.
        issue = gitctx.get(f"/repos/{context.github_repo}/issues/{issue_number}")
        if any(label["name"] == label_name for label in issue["labels"]):
            raise
        labels = issue["labels"]
    return {"labels": labels}


# Assignee Management


@api_router.get("/assignees")
@offload
def get_assignees(gitctx: Annotated[Connector, Depends(connection)]):
    """Get all allowed assignees for the repository"""
    assignees = catalog(gitctx, "assignees")
    return sorted(assignees, key=lambda x: x["login"])


@api_router.post("/issues/{issue_number}/assignees")
@offload
def add_assignee_to_issue(
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
@offload
def remove_assignee_from_issue(
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
