"""Planning equivalence, batching, mutation validation, and pagination regressions.

Generated-by: Codex
Assisted-by: Cline
"""

from copy import deepcopy
from unittest.mock import Mock

from fastapi import HTTPException
import pytest
import requests

from github_pm import api
from github_pm.planning_reader import (
    comment_reactions,
    descendants,
    enrich_issues,
    issue_fields,
)


def page(nodes=(), more=False, cursor=None):
    return {
        "nodes": list(nodes),
        "pageInfo": {"hasNextPage": more, "endCursor": cursor},
    }


def issue(number, **overrides):
    return {
        "id": f"I{number}",
        "databaseId": number * 10,
        "number": number,
        "__typename": "Issue",
        "title": f"Issue {number}",
        "url": f"https://github.com/test/repo/issues/{number}",
        "state": "OPEN",
        "milestone": {"number": 1, "title": "M1"},
        "parent": None,
        "blockedBy": page(),
        "blocking": page(),
        "closedByPullRequestsReferences": page(),
        "issueFieldValues": page(),
        "subIssues": page(),
        **overrides,
    }


def connector(nodes=None):
    nodes = nodes or {}
    git = Mock(spec=api.Connector)
    git.owner, git.repo = "test", "repo"

    def post(path, data=None):
        if path != "/graphql" or data["query"].lstrip().startswith("mutation"):
            return {}
        return {
            "data": {
                "repository": {
                    f"i{k[1:]}": deepcopy(nodes.get(n, issue(n)))
                    for k, n in data["variables"].items()
                    if k.startswith("n")
                }
            }
        }

    git.post.side_effect = post
    git.patch.return_value = {}
    git.delete.return_value = {}
    return git


@pytest.fixture(autouse=True)
def repository(monkeypatch):
    monkeypatch.setattr(api.context, "github_repo", "test/repo")


@pytest.mark.parametrize(
    "priorities,expected",
    [
        ([], [1, 2, 3, 4]),
        (["bug"], [2, 4, 1, 3]),
        (["feature", "bug"], [1, 4, 2, 3]),
        ([" bug ", "feature"], [2, 4, 1, 3]),
    ],
)
async def test_board_preserves_label_sort_and_flat_prs(priorities, expected):
    git = connector()
    git.get_paged.return_value = [
        dict(number=n, id=n, labels=[{"name": name} for name in labels])
        for n, labels in [
            (4, ["BUG", "feature"]),
            (3, []),
            (2, ["bug"]),
            (1, ["feature"]),
        ]
    ] + [dict(number=8, id=8, labels=[], pull_request={})]
    result = await api.get_issues(git, 0, ",".join(priorities))
    assert [i["number"] for i in result["issues"]] == expected
    assert result["pull_requests"][0]["number"] == 8
    assert git.post.call_count == 1
    assert "milestone=none" in git.get_paged.call_args.args[0]


async def test_board_batches_100_issues_and_keeps_relationships():
    nodes = {
        2: issue(2, parent={"number": 1, "title": "Root", "milestone": {"number": 1}}),
        3: issue(
            3, parent={"number": 999, "title": "External", "milestone": {"number": 2}}
        ),
    }
    nodes[1] = issue(
        1,
        blockedBy=page(
            [
                {
                    "databaseId": 90,
                    "number": 9,
                    "title": "Blocker",
                    "url": "u",
                    "state": "OPEN",
                }
            ]
        ),
        closedByPullRequestsReferences=page(
            [{"number": 88, "title": "PR", "url": "p"}]
        ),
    )
    git = connector(nodes)
    git.get_paged.return_value = [
        dict(number=n, id=n, labels=[]) for n in range(1, 101)
    ]
    result = await api.get_issues(git, 1)
    assert git.get_paged.call_count == 1
    assert git.post.call_count == 2
    assert result["issues"][0]["children"][0]["number"] == 2
    assert result["issues"][0]["blocked_by"][0]["id"] == 90
    assert result["issues"][0]["closed_by"][0]["number"] == 88
    assert result["issues"][1]["external_parent"]["number"] == 999
    assert "subIssues(" not in git.post.call_args.args[1]["query"]


async def test_board_attaches_normalized_issue_field_values():
    value = {
        "__typename": "IssueFieldSingleSelectValue",
        "name": "High",
        "value": "High",
        "optionId": "O1",
        "color": "RED",
        "field": {
            "__typename": "IssueFieldSingleSelect",
            "id": "F1",
            "name": "Priority",
            "dataType": "SINGLE_SELECT",
        },
    }
    git = connector({1: issue(1, issueFieldValues=page([value]))})
    git.get_paged.return_value = [dict(number=1, id=1, labels=[])]
    result = await api.get_issues(git, 1)
    assert result["issues"][0]["issue_field_values"] == [
        {
            "field_id": "F1",
            "field_name": "Priority",
            "data_type": "SINGLE_SELECT",
            "value": "High",
            "option_id": "O1",
            "color": "RED",
        }
    ]


def test_issue_fields_normalize_options_and_paginate():
    git = connector()
    git.post.side_effect = [
        {
            "data": {
                "repository": {
                    "viewerCanSeeIssueFields": True,
                    "issueFields": page(
                        [
                            {
                                "__typename": "IssueFieldSingleSelect",
                                "id": "F1",
                                "name": "Priority",
                                "dataType": "SINGLE_SELECT",
                                "options": [
                                    {
                                        "id": "O2",
                                        "name": "Low",
                                        "color": "GREEN",
                                        "priority": 2,
                                    },
                                    {
                                        "id": "O1",
                                        "name": "High",
                                        "color": "RED",
                                        "priority": 1,
                                    },
                                ],
                            }
                        ],
                        True,
                        "next",
                    ),
                }
            }
        },
        {
            "data": {
                "repository": {
                    "viewerCanSeeIssueFields": True,
                    "issueFields": page(
                        [
                            {
                                "__typename": "IssueFieldNumber",
                                "id": "F2",
                                "name": "Estimate",
                                "dataType": "NUMBER",
                            }
                        ]
                    ),
                }
            }
        },
    ]
    can_view, fields = issue_fields(git)
    assert can_view is True
    assert [field["id"] for field in fields] == ["F1", "F2"]
    assert [option["name"] for option in fields[0]["options"]] == ["High", "Low"]
    assert "options" not in fields[1]
    assert git.post.call_args_list[1].args[1]["variables"]["after"] == "next"


async def test_issue_field_updates_set_and_clear_values():
    normalized = [
        {
            "field_id": "F1",
            "field_name": "Priority",
            "data_type": "SINGLE_SELECT",
            "value": "High",
            "option_id": "O1",
            "color": "RED",
        },
        {
            "field_id": "F2",
            "field_name": "Effort",
            "data_type": "SINGLE_SELECT",
            "value": "Medium",
            "option_id": "O2",
            "color": "YELLOW",
        },
    ]
    git = connector()

    def post(path, data=None):
        if data["query"].lstrip().startswith("mutation"):
            return {
                "data": {
                    "setIssueFieldValue": {
                        "issue": {
                            "issueFieldValues": {
                                "nodes": [
                                    {
                                        "__typename": "IssueFieldSingleSelectValue",
                                        "name": "High",
                                        "value": "High",
                                        "optionId": "O1",
                                        "color": "RED",
                                        "field": {
                                            "__typename": "IssueFieldSingleSelect",
                                            "id": "F1",
                                            "name": "Priority",
                                            "dataType": "SINGLE_SELECT",
                                        },
                                    },
                                    {
                                        "__typename": "IssueFieldSingleSelectValue",
                                        "name": "Medium",
                                        "value": "Medium",
                                        "optionId": "O2",
                                        "color": "YELLOW",
                                        "field": {
                                            "__typename": "IssueFieldSingleSelect",
                                            "id": "F2",
                                            "name": "Effort",
                                            "dataType": "SINGLE_SELECT",
                                        },
                                    },
                                ]
                            }
                        }
                    }
                }
            }
        return {"data": {"repository": {"i0": {"__typename": "Issue", "id": "I1"}}}}

    git.post.side_effect = post
    assert await api.update_issue_field_value(
        git, 1, "F1", api.UpdateIssueFieldValue(option_id="O1")
    ) == {"issue_field_values": normalized}
    set_call = git.post.call_args_list[-1].args[1]
    assert set_call["variables"] == {
        "issueId": "I1",
        "fieldId": "F1",
        "optionId": "O1",
    }
    assert await api.update_issue_field_value(
        git, 1, "F1", api.UpdateIssueFieldValue(option_id=None)
    ) == {"issue_field_values": normalized}
    clear_call = git.post.call_args_list[-1].args[1]
    assert clear_call["variables"] == {"issueId": "I1", "fieldId": "F1"}
    assert "delete:true" in clear_call["query"]


async def test_issue_field_catalog_reports_visibility():
    git = connector()
    git.post.side_effect = lambda *args: {
        "data": {
            "repository": {
                "viewerCanSeeIssueFields": False,
                "issueFields": None,
            }
        }
    }
    assert await api.get_issue_fields(git) == {"can_view": False, "fields": []}


def test_nested_links_finish_every_page():
    git = connector({1: issue(1, blocking=page([{"number": 2}], True, "c"))})
    first = git.post.side_effect

    def post(path, data):
        if "node(id:" in data["query"]:
            assert data["variables"]["c0"] == "c"
            return {"data": {"n0": {"blocking": page([{"number": 3}])}}}
        return first(path, data)

    git.post.side_effect = post
    nodes = enrich_issues(git, [{"number": 1}])
    assert [n["number"] for n in nodes[1]["blocking"]["nodes"]] == [2, 3]
    assert git.post.call_count == 2


def test_incomplete_enrichment_is_not_silent_issue_loss():
    git = connector()
    git.post.return_value = {}
    git.post.side_effect = lambda *args: {
        "data": {"repository": {"i0": None}},
        "errors": [{"message": "denied"}],
    }
    with pytest.raises(RuntimeError, match="denied"):
        enrich_issues(git, [{"number": 1}])


async def test_milestone_counts_do_not_download_items():
    git = connector()
    git.post.side_effect = lambda *args: {
        "data": {
            "repository": {
                "milestone": {
                    "issues": {"totalCount": 7},
                    "pullRequests": {"totalCount": 3},
                }
            }
        }
    }
    assert await api.get_milestone_open_counts(git, 5) == {
        "open_issues": 7,
        "open_pull_requests": 3,
    }
    git.get_paged.assert_not_called()
    assert "totalCount" in git.post.call_args.args[1]["query"]
    await api.update_milestone_state(git, 5, api.UpdateMilestoneState(state="closed"))
    git.patch.assert_called_once_with(
        "/repos/test/repo/milestones/5", data={"state": "closed"}
    )


@pytest.mark.parametrize("same", [False, True])
async def test_reparent_reuses_traversal_and_cascades_closed_descendants(same):
    git = connector(
        {
            20: issue(20, subIssues=page([{"number": 30}])),
            30: issue(30, state="CLOSED"),
            10: issue(10, milestone={"number": 1 if same else 2}),
        }
    )
    result = await api.set_issue_parent(git, 20, api.SetIssueParent(parent_number=10))
    assert result["updated_issue_numbers"] == ([] if same else [20, 30])
    queries = [c for c in git.post.call_args_list if c.args[0] == "/graphql"]
    assert len(queries) == 3  # root frontier, child frontier, paired identities
    assert git.patch.call_count == (0 if same else 2)
    git.post.assert_any_call(
        "/repos/test/repo/issues/10/sub_issues",
        data={"sub_issue_id": 200, "replace_parent": True},
    )


@pytest.mark.parametrize("parent", [20, 30])
async def test_reparent_rejects_self_and_descendant(parent):
    git = connector({20: issue(20, subIssues=page([{"number": 30}]))})
    with pytest.raises(HTTPException) as exc:
        await api.set_issue_parent(git, 20, api.SetIssueParent(parent_number=parent))
    assert exc.value.status_code == 422
    git.patch.assert_not_called()


def test_failed_subtree_read_aborts_instead_of_becoming_a_leaf():
    git = connector()
    git.post.side_effect = requests.ConnectionError("unavailable")
    with pytest.raises(requests.ConnectionError):
        descendants(git, 20)


async def test_clear_and_adopt_parent_use_one_identity_read():
    git = connector(
        {
            20: issue(
                20,
                parent={"number": 10, "title": "Root", "milestone": {"number": 2}},
                subIssues=page([{"number": 30}]),
            )
        }
    )
    await api.clear_issue_parent(git, 20)
    git.delete.assert_called_once_with(
        "/repos/test/repo/issues/10/sub_issue", data={"sub_issue_id": 200}
    )
    assert git.post.call_count == 1
    git.post.reset_mock()
    result = await api.adopt_parent_milestone(git, 20)
    assert result["updated_issue_numbers"] == [20, 30]
    assert (result["from_milestone"], result["to_milestone"]) == (1, 2)
    git.get.assert_not_called()


async def test_missing_parent_is_404():
    with pytest.raises(HTTPException) as exc:
        await api.clear_issue_parent(connector(), 20)
    assert exc.value.status_code == 404


@pytest.mark.parametrize("relationship", ["blocked_by", "blocking"])
async def test_dependency_pair_validated_in_one_query(relationship):
    git = connector()
    function = api.add_blocked_by if relationship == "blocked_by" else api.add_blocking
    result = await function(git, 1, api.AddDependency(issue_number=17))
    assert result["linked_issue"]["number"] == 17
    assert result["relationship"] == relationship
    assert git.post.call_count == 2
    git.get.assert_not_called()
    git = connector({17: issue(17, __typename="PullRequest")})
    with pytest.raises(HTTPException) as exc:
        await function(git, 1, api.AddDependency(issue_number=17))
    assert exc.value.status_code == 422


async def test_duplicate_dependency_is_success():
    git = connector()
    read = git.post.side_effect
    response = Mock(status_code=422)
    response.json.return_value = {"message": "already exists"}

    def post(path, data=None):
        if path != "/graphql":
            raise requests.HTTPError(response=response)
        return read(path, data)

    git.post.side_effect = post
    assert (await api.add_blocked_by(git, 1, api.AddDependency(issue_number=17)))[
        "linked_issue"
    ]["number"] == 17


async def test_close_reference_validates_pair_and_keeps_link_fields():
    git = connector({17: issue(17, __typename="PullRequest", id="PR17")})
    result = await api.add_close_reference(
        git, 1, api.AddCloseReference(pull_request_number=17)
    )
    assert result["linked_pull_request"]["number"] == 17
    assert git.post.call_count == 2
    assert git.post.call_args.kwargs["data"]["variables"] == {
        "issueId": "I1",
        "pullRequestIds": ["PR17"],
    }
    with pytest.raises(HTTPException):
        await api.add_close_reference(
            connector(), 1, api.AddCloseReference(pull_request_number=17)
        )


async def test_label_changes_are_single_scoped_writes():
    git = connector()
    git.post.side_effect = None
    git.post.return_value = [{"name": "bug"}, {"name": "other"}]
    assert (await api.add_label_to_issue(git, 1, "bug"))[
        "labels"
    ] == git.post.return_value
    git.post.assert_called_once_with(
        "/repos/test/repo/issues/1/labels", data={"labels": ["bug"]}
    )
    git.delete.return_value = [{"name": "other"}]
    assert (await api.remove_label_from_issue(git, 1, "type/bug"))["labels"] == [
        {"name": "other"}
    ]
    git.delete.assert_called_once_with("/repos/test/repo/issues/1/labels/type%2Fbug")
    git.get.assert_not_called()


async def test_missing_label_is_noop_but_missing_issue_is_error():
    git = connector()
    response = Mock(status_code=404)
    git.delete.side_effect = requests.HTTPError(response=response)
    git.get.return_value = {"labels": []}
    assert await api.remove_label_from_issue(git, 1, "bug") == {"labels": []}
    git.get.side_effect = requests.HTTPError(response=response)
    with pytest.raises(requests.HTTPError):
        await api.remove_label_from_issue(git, 1, "bug")


def test_comments_batch_reactor_names_and_paginate():
    git = connector()
    git.post.side_effect = [
        {
            "data": {
                "nodes": [
                    {
                        "id": "C1",
                        "reactions": page(
                            [{"content": "THUMBS_UP", "user": {"login": "a"}}],
                            True,
                            "next",
                        ),
                    }
                ]
            }
        },
        {"data": {"n0": {"reactions": page([{"content": "HEART", "user": None}])}}},
    ]
    result = comment_reactions(
        git,
        [
            {
                "node_id": "C1",
                "body": "raw",
                "body_html": "html",
                "reactions": {"total_count": 2},
            }
        ],
    )
    assert result[0]["reaction_details"] == [
        {"content": "+1", "user": {"login": "a"}},
        {"content": "heart", "user": None},
    ]
    assert result[0]["body"] == "raw"
    assert git.post.call_count == 2


@pytest.mark.asyncio
async def test_partial_cascade_reports_completed_writes():
    gitctx = connector(
        {
            1: issue(1, subIssues=page([{"number": 2}])),
            2: issue(2),
            3: issue(3, milestone={"number": 9}),
        }
    )
    gitctx.patch.side_effect = [{}, requests.Timeout("ambiguous")]
    with pytest.raises(HTTPException) as caught:
        await api.set_issue_parent(gitctx, 1, api.SetIssueParent(parent_number=3))
    assert caught.value.status_code == 502
    assert caught.value.detail["updated_issue_numbers"] == [1]
    assert caught.value.detail["failed_issue_number"] == 2
    assert caught.value.detail["refresh_required"] is True
    assert gitctx.patch.call_count == 2


@pytest.mark.parametrize("relationship", ["blocked_by", "blocking"])
async def test_dependency_self_link_and_directional_removal(relationship):
    git = connector()
    add = api.add_blocked_by if relationship == "blocked_by" else api.add_blocking
    with pytest.raises(HTTPException) as error:
        await add(git, 1, api.AddDependency(issue_number=1))
    assert error.value.status_code == 422
    git.post.assert_not_called()
    git.get.return_value = {"id": 170 if relationship == "blocked_by" else 10}
    remove = (
        api.remove_blocked_by if relationship == "blocked_by" else api.remove_blocking
    )
    result = await remove(git, 1, 17)
    expected = (
        "/repos/test/repo/issues/1/dependencies/blocked_by/170"
        if relationship == "blocked_by"
        else "/repos/test/repo/issues/17/dependencies/blocked_by/10"
    )
    git.delete.assert_called_once_with(expected)
    assert result["relationship"] == relationship
