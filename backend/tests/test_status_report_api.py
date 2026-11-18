# Assisted-by: Codex
"""Tests for project status report API (mocked GitHub GraphQL).

Generated-by: Cursor
"""

from copy import deepcopy
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest

from github_pm.api import connection
from github_pm.app import app


def _page(nodes):
    return {
        "nodes": deepcopy(nodes),
        "issueCount": len(nodes),
        "pageInfo": {"hasNextPage": False, "endCursor": None},
    }


def _response(body, merged, opened, issues, attention):
    result = {}
    for key, query in body["variables"].items():
        if not key.startswith("q"):
            continue
        nodes = (
            merged
            if "is:merged" in query
            else issues if "is:issue" in query else opened
        )
        result["s" + key[1:]] = _page(nodes)
    if not result:
        nodes = list({n["number"]: deepcopy(n) for n in attention}.values())
        for node in nodes:
            node.setdefault("id", f'P{node["number"]}')
            node.setdefault("reviews", {"nodes": []})["pageInfo"] = _page([])[
                "pageInfo"
            ]
        result["repository"] = {"pullRequests": _page(nodes)}
    return {"data": result}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_connector_graphql():
    gitctx = MagicMock()
    gitctx.owner = "test"
    gitctx.repo = "repo"
    gitctx.status_backlog_nodes = []
    gitctx.status_recently_updated_nodes = []
    gitctx.status_attention_open_nodes = []

    merged_nodes = [
        {
            "number": 10,
            "title": "Merged PR",
            "url": "https://github.com/test/repo/pull/10",
            "mergedAt": "2025-04-06T10:00:00Z",
            "createdAt": "2025-04-01T10:00:00Z",
            "additions": 1,
            "deletions": 1,
            "labels": {"nodes": []},
            "milestone": None,
            "author": {"__typename": "User", "login": "u"},
        }
    ]

    opened_pr_nodes = [
        {
            "__typename": "PullRequest",
            "number": 11,
            "title": "Opened PR",
            "url": "https://github.com/test/repo/pull/11",
            "createdAt": "2025-04-05T12:00:00Z",
            "state": "OPEN",
        }
    ]
    gitctx.status_opened_pr_nodes = opened_pr_nodes

    issue_nodes = [
        {
            "__typename": "Issue",
            "number": 12,
            "title": "New issue",
            "url": "https://github.com/test/repo/issues/12",
            "createdAt": "2025-04-04T12:00:00Z",
        }
    ]
    gitctx.status_opened_issue_nodes = issue_nodes

    def post_side(path, data=None, **kwargs):
        return _response(
            data,
            merged_nodes,
            opened_pr_nodes,
            issue_nodes,
            list(gitctx.status_attention_open_nodes)
            + list(gitctx.status_recently_updated_nodes)
            + list(gitctx.status_backlog_nodes),
        )

    gitctx.post.side_effect = post_side
    return gitctx


class TestProjectStatusReport:
    @pytest.mark.parametrize("is_draft", [False, True])
    def test_report_ok_with_end_date_only_defaults_start(
        self, client, mock_connector_graphql, is_draft
    ):
        mock_connector_graphql.status_opened_pr_nodes[0]["isDraft"] = is_draft

        async def override_conn():
            yield mock_connector_graphql

        app.dependency_overrides[connection] = override_conn
        try:
            r = client.get("/api/v1/project-status", params={"end_date": "2025-04-10"})
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        body = r.json()
        assert body["start_date"] == "2025-04-03"
        assert body["end_date"] == "2025-04-10"
        assert body["merged_pull_requests"] == [
            {
                "number": 10,
                "title": "Merged PR",
                "html_url": "https://github.com/test/repo/pull/10",
            }
        ]
        assert body["opened_pull_requests"] == [
            {
                "number": 11,
                "title": "Opened PR (draft)" if is_draft else "Opened PR",
                "html_url": "https://github.com/test/repo/pull/11",
            }
        ]
        assert body["opened_issues"][0]["number"] == 12
        assert body["second_approval_needed"] == []
        assert body["recently_updated_pull_requests"] == []
        assert body["reviewer_attention_needed"] == []
        assert body["creator_attention_needed"] == []
        assert body["pr_backlog"] == []

    @pytest.mark.parametrize(
        ("created_at", "closed_at", "included"),
        [
            ("2025-04-03T00:00:00Z", None, True),
            ("2025-04-10T23:59:59Z", None, True),
            ("2025-04-03T00:00:00Z", "2025-04-03T00:00:00Z", False),
            ("2025-04-04T12:00:00Z", "2025-04-06T12:00:00Z", False),
            ("2025-04-04T12:00:00Z", "2025-04-10T23:59:59Z", False),
            ("2025-04-04T12:00:00Z", "2025-04-11T00:00:00Z", True),
            ("2025-04-04T12:00:00Z", "2025-04-11T01:00:00+02:00", False),
            ("2025-04-02T23:59:59Z", None, False),
            ("2025-04-11T00:00:00Z", None, False),
        ],
    )
    def test_opened_issues_exclude_closures_during_report_period(
        self, client, mock_connector_graphql, created_at, closed_at, included
    ):
        """Keep new issues unless their closure falls in the reporting interval.

        Generated-by: Codex
        """
        issue = mock_connector_graphql.status_opened_issue_nodes[0]
        issue.update(createdAt=created_at, closedAt=closed_at)

        async def override_conn():
            yield mock_connector_graphql

        app.dependency_overrides[connection] = override_conn
        try:
            response = client.get(
                "/api/v1/project-status",
                params={"start_date": "2025-04-03", "end_date": "2025-04-10"},
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        numbers = [item["number"] for item in response.json()["opened_issues"]]
        assert numbers == ([12] if included else [])

    def test_report_single_calendar_day(self, client, mock_connector_graphql):
        async def override_conn():
            yield mock_connector_graphql

        app.dependency_overrides[connection] = override_conn
        try:
            r = client.get(
                "/api/v1/project-status",
                params={"start_date": "2025-04-10", "end_date": "2025-04-10"},
            )
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        body = r.json()
        assert body["start_date"] == "2025-04-10"
        assert body["end_date"] == "2025-04-10"
        assert body["opened_pull_requests"] == []

    def test_report_explicit_range(self, client, mock_connector_graphql):
        async def override_conn():
            yield mock_connector_graphql

        app.dependency_overrides[connection] = override_conn
        try:
            r = client.get(
                "/api/v1/project-status",
                params={"start_date": "2025-03-28", "end_date": "2025-04-10"},
            )
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        body = r.json()
        assert body["start_date"] == "2025-03-28"
        assert body["end_date"] == "2025-04-10"

    def test_start_after_end(self, client, mock_connector_graphql):
        async def override_conn():
            yield mock_connector_graphql

        app.dependency_overrides[connection] = override_conn
        try:
            r = client.get(
                "/api/v1/project-status",
                params={"start_date": "2025-04-11", "end_date": "2025-04-10"},
            )
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 422

    def test_range_too_long(self, client, mock_connector_graphql):
        async def override_conn():
            yield mock_connector_graphql

        app.dependency_overrides[connection] = override_conn
        try:
            r = client.get(
                "/api/v1/project-status",
                params={"start_date": "2024-01-01", "end_date": "2025-01-02"},
            )
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 422

    def test_graphql_queries_cover_window(self, client, mock_connector_graphql):
        async def override_conn():
            yield mock_connector_graphql

        app.dependency_overrides[connection] = override_conn
        try:
            client.get(
                "/api/v1/project-status",
                params={"start_date": "2025-04-04", "end_date": "2025-04-10"},
            )
        finally:
            app.dependency_overrides.clear()

        gql_qs = []
        for c in mock_connector_graphql.post.call_args_list:
            args = getattr(c, "args", ())
            body = args[1] if len(args) >= 2 else getattr(c, "kwargs", {}).get("data")
            if isinstance(body, dict) and body.get("variables"):
                gql_qs.extend(
                    v for k, v in body["variables"].items() if k.startswith("q")
                )

        assert any("merged:2025-04-04..2025-04-10" in q for q in gql_qs)
        assert any("is:merged" in q for q in gql_qs)
        assert any(
            "repo:test/repo is:pr created:2025-04-04..2025-04-10" in q for q in gql_qs
        )
        assert any(
            "repo:test/repo is:issue created:2025-04-04..2025-04-10" in q
            for q in gql_qs
        )
        assert len(gql_qs) == 3
        assert mock_connector_graphql.post.call_count == 2
        search_query = mock_connector_graphql.post.call_args_list[0].args[1]["query"]
        assert "isDraft" in search_query
        assert "closedAt" in search_query
        open_query = mock_connector_graphql.post.call_args.args[1]["query"]
        assert "pullRequests(states:[OPEN]" in open_query
        assert "additions" not in open_query
        assert "labels" not in open_query

    def test_attention_sections_partition_open_prs(
        self, client, mock_connector_graphql
    ):
        mock_connector_graphql.status_attention_open_nodes = [
            {
                "number": 70,
                "title": "Needs first review",
                "url": "https://github.com/test/repo/pull/70",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-04-05T12:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "CLEAN",
                "reviews": {"nodes": []},
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
            {
                "number": 71,
                "title": "Pushed after review",
                "url": "https://github.com/test/repo/pull/71",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-04-06T12:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "CLEAN",
                "reviews": {
                    "nodes": [
                        {
                            "submittedAt": "2025-04-03T10:00:00Z",
                            "state": "COMMENTED",
                        }
                    ]
                },
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
            {
                "number": 72,
                "title": "Needs author response",
                "url": "https://github.com/test/repo/pull/72",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-04-05T12:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "CLEAN",
                "reviews": {
                    "nodes": [
                        {
                            "submittedAt": "2025-04-07T10:00:00Z",
                            "state": "CHANGES_REQUESTED",
                        }
                    ]
                },
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
            {
                "number": 73,
                "title": "Conflicted",
                "url": "https://github.com/test/repo/pull/73",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-04-04T12:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "mergeable": "CONFLICTING",
                "mergeStateStatus": "DIRTY",
                "reviews": {"nodes": []},
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
            {
                "number": 74,
                "title": "Behind base branch",
                "url": "https://github.com/test/repo/pull/74",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-04-05T12:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "BEHIND",
                "reviews": {"nodes": []},
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
            {
                "number": 75,
                "title": "Needs second approval",
                "url": "https://github.com/test/repo/pull/75",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-04-05T12:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "CLEAN",
                "reviews": {
                    "nodes": [
                        {
                            "submittedAt": "2025-04-04T10:00:00Z",
                            "state": "APPROVED",
                            "author": {"__typename": "User", "login": "reviewer"},
                        }
                    ]
                },
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
            {
                "number": 76,
                "title": "Already has two approvals",
                "url": "https://github.com/test/repo/pull/76",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-04-05T12:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "mergeable": "MERGEABLE",
                "mergeStateStatus": "CLEAN",
                "reviews": {
                    "nodes": [
                        {
                            "submittedAt": "2025-04-03T10:00:00Z",
                            "state": "APPROVED",
                        },
                        {
                            "submittedAt": "2025-04-04T10:00:00Z",
                            "state": "APPROVED",
                        },
                    ]
                },
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
        ]

        async def override_conn():
            yield mock_connector_graphql

        app.dependency_overrides[connection] = override_conn
        try:
            r = client.get(
                "/api/v1/project-status",
                params={"start_date": "2025-04-04", "end_date": "2025-04-10"},
            )
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        body = r.json()
        assert {p["number"] for p in body["reviewer_attention_needed"]} == {
            70,
            71,
            75,
            76,
        }
        assert body["second_approval_needed"] == [
            {
                "number": 75,
                "title": "Needs second approval",
                "html_url": "https://github.com/test/repo/pull/75",
                "reviewer_login": "reviewer",
            }
        ]
        assert {p["number"] for p in body["creator_attention_needed"]} == {72, 73, 74}

    def test_recently_updated_pull_requests_excludes_opened_in_window(
        self, client, mock_connector_graphql
    ):
        mock_connector_graphql.status_recently_updated_nodes = [
            {
                "number": 60,
                "title": "Older PR touched now",
                "url": "https://github.com/test/repo/pull/60",
                "createdAt": "2025-01-10T10:00:00Z",
                "updatedAt": "2025-04-06T15:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
            {
                "number": 61,
                "title": "Opened and updated same window",
                "url": "https://github.com/test/repo/pull/61",
                "createdAt": "2025-04-05T12:00:00Z",
                "updatedAt": "2025-04-06T15:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
            {
                "number": 62,
                "title": "Draft touched",
                "url": "https://github.com/test/repo/pull/62",
                "createdAt": "2025-01-10T10:00:00Z",
                "updatedAt": "2025-04-06T15:00:00Z",
                "state": "OPEN",
                "isDraft": True,
                "mergedAt": None,
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
        ]

        async def override_conn():
            yield mock_connector_graphql

        app.dependency_overrides[connection] = override_conn
        try:
            r = client.get(
                "/api/v1/project-status",
                params={"start_date": "2025-04-04", "end_date": "2025-04-10"},
            )
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        recent = r.json()["recently_updated_pull_requests"]
        assert recent == [
            {
                "number": 60,
                "title": "Older PR touched now",
                "html_url": "https://github.com/test/repo/pull/60",
            }
        ]

    def test_pr_backlog_includes_open_prs_updated_before_start(
        self, client, mock_connector_graphql
    ):
        mock_connector_graphql.status_backlog_nodes = [
            {
                "number": 50,
                "title": "Stale open",
                "url": "https://github.com/test/repo/pull/50",
                "createdAt": "2025-01-01T10:00:00Z",
                "updatedAt": "2025-04-03T23:59:59Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
            {
                "number": 51,
                "title": "Touched on start day",
                "url": "https://github.com/test/repo/pull/51",
                "createdAt": "2025-01-01T10:00:00Z",
                "updatedAt": "2025-04-04T00:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
            {
                "number": 52,
                "title": "Stale draft",
                "url": "https://github.com/test/repo/pull/52",
                "createdAt": "2025-01-01T10:00:00Z",
                "updatedAt": "2025-04-03T10:00:00Z",
                "state": "OPEN",
                "isDraft": True,
                "mergedAt": None,
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
        ]

        async def override_conn():
            yield mock_connector_graphql

        app.dependency_overrides[connection] = override_conn
        try:
            r = client.get(
                "/api/v1/project-status",
                params={"start_date": "2025-04-04", "end_date": "2025-04-10"},
            )
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        backlog = r.json()["pr_backlog"]
        assert backlog == [
            {
                "number": 50,
                "title": "Stale open",
                "html_url": "https://github.com/test/repo/pull/50",
                "days_since_update": 7,
            }
        ]

    def test_pr_backlog_sorted_by_age_descending(self, client, mock_connector_graphql):
        """PR backlog lists stalest PRs first (days_since_update), not by PR number."""
        mock_connector_graphql.status_backlog_nodes = [
            {
                "number": 50,
                "title": "Recently stale",
                "url": "https://github.com/test/repo/pull/50",
                "createdAt": "2025-01-01T10:00:00Z",
                "updatedAt": "2025-04-03T12:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
            {
                "number": 100,
                "title": "Very stale",
                "url": "https://github.com/test/repo/pull/100",
                "createdAt": "2025-01-01T10:00:00Z",
                "updatedAt": "2025-04-01T10:00:00Z",
                "state": "OPEN",
                "isDraft": False,
                "mergedAt": None,
                "additions": 1,
                "deletions": 0,
                "labels": {"nodes": []},
                "milestone": None,
                "author": {"__typename": "User", "login": "u"},
            },
        ]

        async def override_conn():
            yield mock_connector_graphql

        app.dependency_overrides[connection] = override_conn
        try:
            r = client.get(
                "/api/v1/project-status",
                params={"start_date": "2025-04-04", "end_date": "2025-04-10"},
            )
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        backlog = r.json()["pr_backlog"]
        assert [row["number"] for row in backlog] == [100, 50]
        assert [row["days_since_update"] for row in backlog] == [9, 7]

    def test_opened_prs_exclude_closed_and_merged(self, client):
        """Only PRs with GitHub state OPEN appear in opened_pull_requests."""
        gitctx = MagicMock()
        gitctx.owner = "test"
        gitctx.repo = "repo"

        merged_nodes = []

        opened_pr_nodes = [
            {
                "__typename": "PullRequest",
                "number": 20,
                "title": "Still open",
                "url": "https://github.com/test/repo/pull/20",
                "createdAt": "2025-04-05T12:00:00Z",
                "state": "OPEN",
            },
            {
                "__typename": "PullRequest",
                "number": 21,
                "title": "Merged same window",
                "url": "https://github.com/test/repo/pull/21",
                "createdAt": "2025-04-05T12:00:00Z",
                "state": "MERGED",
            },
            {
                "__typename": "PullRequest",
                "number": 22,
                "title": "Closed without merge",
                "url": "https://github.com/test/repo/pull/22",
                "createdAt": "2025-04-05T12:00:00Z",
                "state": "CLOSED",
            },
        ]

        issue_nodes = []

        def post_side(path, data=None, **kwargs):
            return _response(data, merged_nodes, opened_pr_nodes, issue_nodes, [])

        gitctx.post.side_effect = post_side

        async def override_conn():
            yield gitctx

        app.dependency_overrides[connection] = override_conn
        try:
            r = client.get(
                "/api/v1/project-status",
                params={"start_date": "2025-04-04", "end_date": "2025-04-10"},
            )
        finally:
            app.dependency_overrides.clear()

        assert r.status_code == 200
        opened = r.json()["opened_pull_requests"]
        numbers = {p["number"] for p in opened}
        assert numbers == {20}
        assert r.json()["recently_updated_pull_requests"] == []
        assert r.json()["reviewer_attention_needed"] == []
        assert r.json()["creator_attention_needed"] == []
        assert r.json()["pr_backlog"] == []
