from collections import defaultdict
from datetime import datetime
import time
from typing import Annotated, Any, AsyncGenerator

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
import requests

from github_pm.context import context
from github_pm.logger import logger

api_router = APIRouter()


class Connector:

    def __init__(self, github_token: str):
        """Initialize a GitHub connection.

        Args:
            github_token: The GitHub Personal Access Token to use
        """
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        self.owner, self.repo = context.github_repo.split("/", maxsplit=1)
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
            context.github_repo,
        )

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict:
        response = self.github.get(f"{self.base_url}{path}", headers=headers)
        response.raise_for_status()
        self.response = response
        return response.json()

    def get_paged(self, path: str, headers: dict[str, str] | None = None) -> list[dict]:
        url: str | None = f"{self.base_url}{path}"
        results = []
        while url:
            response = self.github.get(url, headers=headers)
            response.raise_for_status()
            self.response = response
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

    def patch(
        self, path: str, data: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict:
        response = self.github.patch(
            f"{self.base_url}{path}", json=data, headers=headers
        )
        response.raise_for_status()
        self.response = response
        return response.json()

    def post(
        self, path: str, data: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict:
        response = self.github.post(
            f"{self.base_url}{path}", json=data, headers=headers
        )
        response.raise_for_status()
        self.response = response
        return response.json()

    def delete(self, path: str, headers: dict[str, str] | None = None) -> dict:
        response = self.github.delete(f"{self.base_url}{path}", headers=headers)
        response.raise_for_status()
        self.response = response
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


@api_router.get("/issues/{milestone_number}")
async def get_issues(
    gitctx: Annotated[Connector, Depends(connection)],
    milestone_number: Annotated[int, Path(title="Milestone")],
    sort: Annotated[
        str | None, Query(title="Sort", description="List of labels to sort by")
    ] = None,
):
    if sort:
        sort_by = [s.strip() for s in sort.split(",")]
    else:
        sort_by = []
    sorted_issues = defaultdict(list)
    start = time.time()
    milestone = "none" if milestone_number == 0 else milestone_number
    issues = gitctx.get_paged(
        f"/repos/{context.github_repo}/issues?milestone={milestone}&state=open",
        headers={"Accept": "application/vnd.github.html+json"},
    )
    for i in issues:
        labels = set([label["name"].lower() for label in i["labels"]])
        if "pull_request" not in i:
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
                            "issue": i["number"],
                        },
                    },
                )
                data = response["data"]
                issue_node = data["repository"]["issue"]
                closed = issue_node["closedByPullRequestsReferences"]["nodes"]
                if len(closed) > 0:
                    i["closed_by"] = [
                        {
                            "number": linked["number"],
                            "title": linked["title"],
                            "url": linked["url"],
                        }
                        for linked in closed
                    ]
            except Exception as e:
                logger.exception(
                    f"Error finding linked PRs for issue {i['number']}: {e!r}"
                )
                continue
        for label in sort_by:
            if label in labels:
                sorted_issues[label].append(i)
                break
        else:
            sorted_issues["other"].append(i)
    all_issues = []
    for label in sort_by + ["other"]:
        all_issues.extend(sorted_issues[label])
    logger.debug(
        f"{len(issues)}({len(all_issues)}) issues: {time.time() - start:.3f} seconds"
    )
    return all_issues


@api_router.get("/comments/{issue_number}")
async def get_comments(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
):
    start = time.time()
    comments = gitctx.get_paged(
        f"/repos/{context.github_repo}/issues/{issue_number}/comments",
        headers={"Accept": "application/vnd.github.html+json"},
    )
    logger.debug(
        f"{len(comments)} issue {issue_number} comments: {time.time() - start:.3f} seconds"
    )
    return comments


@api_router.get("/issues/{issue_number}/reactions")
async def get_issue_reactions(
    gitctx: Annotated[Connector, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
):
    start = time.time()
    reactions = gitctx.get_paged(
        f"/repos/{context.github_repo}/issues/{issue_number}/reactions",
        headers={"Accept": "application/vnd.github.html+json"},
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
        headers={"Accept": "application/vnd.github.html+json"},
    )
    return reactions


# """Milestone Management"""


@api_router.get("/milestones")
async def get_milestones(gitctx: Annotated[Connector, Depends(connection)]):
    milestones = gitctx.get_paged(
        f"/repos/{context.github_repo}/milestones",
        headers={"Accept": "application/vnd.github.html+json"},
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
        data={"milestone": milestone_number},
    )
    return issue


# """Label Management"""


@api_router.get("/labels")
async def get_labels(gitctx: Annotated[Connector, Depends(connection)]):
    labels = gitctx.get_paged(
        f"/repos/{context.github_repo}/labels",
        headers={"Accept": "application/vnd.github.html+json"},
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
