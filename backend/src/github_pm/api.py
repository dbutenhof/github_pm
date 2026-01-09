from collections import defaultdict
from dataclasses import dataclass
from datetime import date
import time
from typing import Annotated, AsyncGenerator

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from github import Auth, Github, Repository
from github.GithubObject import NotSet
from pydantic import BaseModel, Field

from github_pm.context import context

api_router = APIRouter()


@dataclass
class GitHubCtx:
    github: Github
    repo: Repository


async def connection() -> AsyncGenerator[GitHubCtx, None]:
    """FastAPI Dependency to open & close Github connections"""
    gh = None
    print(f"Opening GitHub connection for repo {context.github_repo}")
    try:
        gh = Github(auth=Auth.Token(context.github_token))
    except Exception as e:
        print(f"Error opening GitHub service: {e}")
        raise HTTPException(
            status_code=400, detail=f"Can't open GitHub connection: {str(e)!r}"
        )
    try:
        # yield the repository object
        repo = gh.get_repo(context.github_repo)
        print(f"Repository: {repo.name}")
        yield GitHubCtx(github=gh, repo=repo)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error interacting with GitHub: {type(e).__name__}->{str(e)!r}")
        raise HTTPException(
            status_code=400, detail=f"Can't interact with GitHub: {str(e)!r}"
        )
    finally:
        if gh:
            gh.close()


@api_router.get("/project")
async def get_project():
    return {
        "app_name": context.app_name,
        "github_repo": context.github_repo,
    }


@api_router.get("/issues/{milestone_number}")
async def get_issues(
    gitctx: Annotated[GitHubCtx, Depends(connection)],
    milestone_number: Annotated[int, Path(title="Milestone")],
    sort: Annotated[
        str | None, Query(title="Sort", description="List of labels to sort by")
    ] = None,
):
    repo = gitctx.repo
    if sort:
        sort_by = [s.strip() for s in sort.split(",")]
    else:
        sort_by = []
    sorted_issues = defaultdict(list)
    start = time.time()
    if milestone_number == 0:
        milestone = "none"
    else:
        milestone = repo.get_milestone(milestone_number)
        print(
            f"[Milestone {milestone_number} found: {milestone.title}: {time.time() - start:.3f} seconds]"
        )
    issues = repo.get_issues(milestone=milestone, state="open")
    for i in issues:
        labels = set([label.name.lower() for label in i.labels])
        if "pull_request" not in i.raw_data:
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
            owner, repo = context.github_repo.split("/", maxsplit=1)
            try:
                gql_response = gitctx.github.requester.graphql_query(
                    query=query,
                    variables={
                        "owner": owner,
                        "repo": repo,
                        "issue": i.number,
                    },
                )
                data = gql_response[1]["data"]
                issue_node = data["repository"]["issue"]
                closed = issue_node["closedByPullRequestsReferences"]["nodes"]
                if len(closed) > 0:
                    i.raw_data["closed_by"] = [
                        {
                            "number": linked["number"],
                            "title": linked["title"],
                            "url": linked["url"],
                        }
                        for linked in closed
                    ]
            except Exception as e:
                print(
                    f"Error finding linked PRs for issue {i.number}: {e!r}", flush=True
                )
                continue
        for label in sort_by:
            if label in labels:
                sorted_issues[label].append(i.raw_data)
                break
        else:
            sorted_issues["other"].append(i.raw_data)
    all_issues = []
    for label in sort_by + ["other"]:
        all_issues.extend(sorted_issues[label])
    print(
        f"[{issues.totalCount}({len(all_issues)}) issues: {time.time() - start:.3f} seconds]"
    )
    return all_issues


@api_router.get("/comments/{issue_number}")
async def get_comments(
    gitctx: Annotated[GitHubCtx, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
):
    start = time.time()
    comments = gitctx.repo.get_issue(issue_number).get_comments()
    simplified = [i.raw_data for i in comments]
    print(f"[{len(simplified)} comments: {time.time() - start:.3f} seconds]")
    return simplified


"""Milestone Management"""


@api_router.get("/milestones")
async def get_milestones(gitctx: Annotated[GitHubCtx, Depends(connection)]):
    repo = gitctx.repo
    milestones = repo.get_milestones()
    response = [
        {
            "title": m.title,
            "number": m.number,
            "description": m.description,
            "due_on": m.due_on,
        }
        for m in milestones
    ]
    response.append(
        {
            "title": "none",
            "number": 0,
            "description": "No milestone",
            "due_on": None,
        }
    )
    return response


class CreateMilestone(BaseModel):
    title: str = Field(title="Milestone Title")
    description: str = Field(default=NotSet, title="Milestone Description")
    due_on: date = Field(default=NotSet, title="Milestone Due Date")


@api_router.post("/milestones")
async def create_milestone(
    gitctx: Annotated[GitHubCtx, Depends(connection)],
    milestone: Annotated[CreateMilestone, Body(title="Milestone")],
):
    start = time.time()
    print(f"Creating milestone: {milestone!r}", flush=True)
    try:
        m = gitctx.repo.create_milestone(
            title=milestone.title,
            state="open",
            description=milestone.description,
            due_on=milestone.due_on,
        )
        print(
            f"[{milestone.title} milestone created: {time.time() - start:.3f} seconds]"
        )
        return m.raw_data
    except Exception as e:
        raise
        print(f"Error creating milestone: {e!r}", flush=True)
        raise HTTPException(
            status_code=400, detail=f"Can't create milestone: {str(e)!r}"
        )


@api_router.delete("/milestones/{milestone_number}")
async def delete_milestone(
    gitctx: Annotated[GitHubCtx, Depends(connection)],
    milestone_number: Annotated[int, Path(title="Milestone")],
):
    start = time.time()
    try:
        milestone = gitctx.repo.get_milestone(milestone_number)
    except Exception as e:
        print(f"Milestone not found: {milestone_number!r}", flush=True)
        raise HTTPException(
            status_code=400,
            detail=f"Milestone {milestone_number!r} not found: {str(e)!r}",
        )
    try:
        milestone.delete()
        print(
            f"[{milestone_number} milestone deleted: {time.time() - start:.3f} seconds]"
        )
        return {"message": f"{milestone_number} milestone deleted"}
    except Exception as e:
        print(f"Error deleting milestone: {e!r}", flush=True)
        raise HTTPException(
            status_code=400, detail=f"Can't delete milestone: {str(e)!r}"
        ) from e


@api_router.post("/issues/{issue_number}/milestone/{milestone_number}")
async def add_milestone_to_issue(
    gitctx: Annotated[GitHubCtx, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    milestone_number: Annotated[int, Path(title="Milestone")],
):
    start = time.time()
    issue = gitctx.repo.get_issue(issue_number)
    milestone = gitctx.repo.get_milestone(milestone_number)
    issue.edit(milestone=milestone)
    print(
        f"[{milestone_number} milestone added to issue {issue_number}: {time.time() - start:.3f} seconds]"
    )
    return {"message": f"{milestone_number} milestone added to issue {issue_number}"}


@api_router.delete("/issues/{issue_number}/milestone/{milestone_number}")
async def remove_milestone_from_issue(
    gitctx: Annotated[GitHubCtx, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    milestone_number: Annotated[int, Path(title="Milestone")],
):
    start = time.time()
    issue = gitctx.repo.get_issue(issue_number)
    issue.edit(milestone=None)
    print(
        f"[{milestone_number} milestone removed from issue {issue_number}: {time.time() - start:.3f} seconds]"
    )
    return {
        "message": f"{milestone_number} milestone removed from issue {issue_number}"
    }


"""Label Management"""


@api_router.get("/labels")
async def get_labels(gitctx: Annotated[GitHubCtx, Depends(connection)]):
    start = time.time()
    labels = [label.raw_data for label in gitctx.repo.get_labels()]
    print(f"[{len(labels)} labels: {time.time() - start:.3f} seconds]")
    return labels


class CreateLabel(BaseModel):
    name: str = Field(title="Label Name")
    color: str = Field(title="Label Color")
    description: str = Field(default=NotSet, title="Label Description")


@api_router.post("/labels")
async def create_label(
    gitctx: Annotated[GitHubCtx, Depends(connection)],
    label: Annotated[CreateLabel, Body(title="Label")],
):
    start = time.time()
    try:
        label = gitctx.repo.create_label(
            name=label.name, color=label.color, description=label.description
        )
        print(f"[{label.name} label created: {time.time() - start:.3f} seconds]")
        return label.raw_data
    except Exception as e:
        raise
        print(f"Error creating label: {e}", flush=True)
        raise HTTPException(status_code=400, detail=f"Can't create label: {str(e)!r}")


@api_router.delete("/labels/{label_name}")
async def delete_label(
    gitctx: Annotated[GitHubCtx, Depends(connection)], label_name: str
):
    start = time.time()
    try:
        label = gitctx.repo.get_label(label_name)
    except Exception as e:
        print(f"Label not found: {label_name!r}", flush=True)
        raise HTTPException(
            status_code=400, detail=f"Label {label_name!r} not found: {str(e)!r}"
        )
    try:
        label.delete()
        print(f"[{label_name} label deleted: {time.time() - start:.3f} seconds]")
        return {"message": f"{label_name} label deleted"}
    except Exception as e:
        print(f"Error deleting label: {e}", flush=True)
        raise HTTPException(status_code=400, detail=f"Can't delete label: {str(e)!r}")


@api_router.post("/issues/{issue_number}/labels/{label_name}")
async def add_label_to_issue(
    gitctx: Annotated[GitHubCtx, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    label_name: Annotated[str, Path(title="Label")],
):
    start = time.time()
    issue = gitctx.repo.get_issue(issue_number)
    issue.add_to_labels(label_name)
    print(
        f"[{label_name} label added to issue {issue_number}: {time.time() - start:.3f} seconds]"
    )
    return {"message": f"{label_name} label added to issue {issue_number}"}


@api_router.delete("/issues/{issue_number}/labels/{label_name}")
async def remove_label_from_issue(
    gitctx: Annotated[GitHubCtx, Depends(connection)],
    issue_number: Annotated[int, Path(title="Issue")],
    label_name: Annotated[str, Path(title="Label")],
):
    start = time.time()
    issue = gitctx.repo.get_issue(issue_number)
    issue.remove_from_labels(label_name)
    print(
        f"[{label_name} label removed from issue {issue_number}: {time.time() - start:.3f} seconds]"
    )
    return
