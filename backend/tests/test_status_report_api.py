"""Tests for project status report API (mocked GitHub GraphQL).

Generated-by: Cursor
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pytest

from github_pm.api import connection
from github_pm.app import app


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

    issue_nodes = [
        {
            "__typename": "Issue",
            "number": 12,
            "title": "New issue",
            "url": "https://github.com/test/repo/issues/12",
            "createdAt": "2025-04-04T12:00:00Z",
        }
    ]

    def post_side(path: str, data=None, **kwargs):
        body = data
        if path != "/graphql" or not isinstance(body, dict):
            raise AssertionError(f"unexpected post {path=!r} body={body!r}")
        q = (body.get("variables") or {}).get("q") or ""
        if "is:merged" in q and "merged:" in q:
            return {
                "data": {
                    "search": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": merged_nodes,
                    }
                }
            }
        if "is:issue" in q and "created:" in q:
            return {
                "data": {
                    "search": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": issue_nodes,
                    }
                }
            }
        if "is:pr" in q and "is:open" in q and "updated:" in q:
            if "updated:<" in q:
                return {
                    "data": {
                        "search": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": list(gitctx.status_backlog_nodes),
                        }
                    }
                }
            return {
                "data": {
                    "search": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": list(gitctx.status_recently_updated_nodes),
                    }
                }
            }
        if "is:pr" in q and "created:" in q:
            return {
                "data": {
                    "search": {
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": opened_pr_nodes,
                    }
                }
            }
        raise AssertionError(f"unexpected graphql q={q!r}")

    gitctx.post.side_effect = post_side
    return gitctx


class TestProjectStatusReport:
    def test_report_ok_with_end_date_only_defaults_start(
        self, client, mock_connector_graphql
    ):
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
        assert body["opened_pull_requests"][0]["number"] == 11
        assert body["opened_issues"][0]["number"] == 12
        assert body["recently_updated_pull_requests"] == []
        assert body["pr_backlog"] == []

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
                gql_qs.append(body["variables"].get("q") or "")

        assert any("merged:2025-04-04..2025-04-10" in q for q in gql_qs)
        assert any("is:merged" in q for q in gql_qs)
        assert any(
            "repo:test/repo is:pr created:2025-04-04..2025-04-10" in q for q in gql_qs
        )
        assert any(
            "repo:test/repo is:issue created:2025-04-04..2025-04-10" in q
            for q in gql_qs
        )
        assert any(
            "repo:test/repo is:pr is:open draft:false updated:<2025-04-04" in q
            for q in gql_qs
        )
        assert any(
            "repo:test/repo is:pr is:open draft:false updated:2025-04-04..2025-04-10"
            in q
            for q in gql_qs
        )

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

    def test_opened_prs_exclude_closed_without_merge(self, client):
        """PRs with GitHub state CLOSED (not merged) must not appear in opened_pull_requests."""
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

        def post_side(path: str, data=None, **kwargs):
            body = data
            if path != "/graphql" or not isinstance(body, dict):
                raise AssertionError(f"unexpected post {path=!r} body={body!r}")
            q = (body.get("variables") or {}).get("q") or ""
            if "is:merged" in q and "merged:" in q:
                return {
                    "data": {
                        "search": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": merged_nodes,
                        }
                    }
                }
            if "is:issue" in q and "created:" in q:
                return {
                    "data": {
                        "search": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": issue_nodes,
                        }
                    }
                }
            if "is:pr" in q and "is:open" in q and "updated:" in q:
                if "updated:<" in q:
                    return {
                        "data": {
                            "search": {
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                                "nodes": [],
                            }
                        }
                    }
                return {
                    "data": {
                        "search": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [],
                        }
                    }
                }
            if "is:pr" in q and "created:" in q:
                return {
                    "data": {
                        "search": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": opened_pr_nodes,
                        }
                    }
                }
            raise AssertionError(f"unexpected graphql q={q!r}")

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
        assert numbers == {20, 21}
        assert r.json()["recently_updated_pull_requests"] == []
        assert r.json()["pr_backlog"] == []
