"""Tests for SDLC KPI API routes (mocked GitHub)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest

from github_pm.app import app
from github_pm.api import connection


def _graphql_page(nodes: list, has_next: bool = False, cursor: str | None = "c1"):
    return {
        "data": {
            "search": {
                "pageInfo": {
                    "hasNextPage": has_next,
                    "endCursor": cursor if has_next else None,
                },
                "nodes": nodes,
            }
        }
    }


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_connector():
    gitctx = MagicMock()
    gitctx.owner = "test"
    gitctx.repo = "repo"
    gitctx.base_url = "https://api.github.com"

    _human = {"__typename": "User", "login": "contributor"}
    merged_node = {
        "number": 10,
        "createdAt": "2025-04-05T10:00:00Z",
        "mergedAt": "2025-04-06T10:00:00Z",
        "additions": 5,
        "deletions": 5,
        "labels": {"nodes": [{"name": "enhancement"}]},
        "milestone": None,
        "author": _human,
    }
    opened_node = {
        "number": 11,
        "createdAt": "2025-04-05T12:00:00Z",
        "mergedAt": None,
        "additions": 2,
        "deletions": 2,
        "labels": {"nodes": [{"name": "bug"}]},
        "milestone": None,
        "author": _human,
    }

    def post_side(path: str, payload: dict):
        q = payload["variables"]["q"]
        if "is:merged" in q:
            return _graphql_page([merged_node])
        return _graphql_page([opened_node])

    gitctx.post.side_effect = post_side

    def get_side(path: str, headers=None):
        if "/pulls/11/reviews" in path:
            return [
                {
                    "user": {"login": "rev", "type": "User"},
                    "submitted_at": "2025-04-05T14:00:00Z",
                }
            ]
        if "/search/issues" in path:
            return {"total_count": 3}
        raise AssertionError(f"unexpected GET {path}")

    gitctx.get.side_effect = get_side
    return gitctx


class TestSdlcDelivery:
    def test_delivery_ok(self, client, mock_connector):
        fixed = datetime(2025, 4, 10, 12, 0, 0, tzinfo=UTC)

        async def override_conn():
            yield mock_connector

        with (
            patch("github_pm.sdlc_metrics.utc_now", return_value=fixed),
            patch("github_pm.sdlc_api.context") as ctx,
        ):
            ctx.github_repo = "test/repo"
            ctx.sdlc_feature_labels = "enhancement"
            ctx.sdlc_bug_labels = "bug"
            ctx.sdlc_docs_labels = "documentation"
            app.dependency_overrides[connection] = override_conn
            try:
                r = client.get("/api/v1/sdlc/delivery?weeks=1&week_days=7")
            finally:
                app.dependency_overrides.clear()

        assert r.status_code == 200
        data = r.json()
        assert data["weeks"] == 1
        assert data["week_days"] == 7
        assert len(data["slices"]) == 1
        s0 = data["slices"][0]
        assert s0["window_days"] == 7
        assert s0["merged_pr_throughput"]["total"] == 1
        assert s0["median_pr_cycle_time"]["pr_count"] == 1
        assert s0["median_time_to_first_review"]["eligible_pr_count"] == 1
        assert s0["median_time_to_first_review"]["included_pr_count"] == 1


class TestEscapedDefect:
    def test_escaped_defect_rate(self, client, mock_connector):
        fixed = datetime(2025, 4, 10, 12, 0, 0, tzinfo=UTC)
        _human = {"__typename": "User", "login": "contributor"}
        feat = {
            "number": 1,
            "createdAt": "2025-04-01T10:00:00Z",
            "mergedAt": "2025-04-08T10:00:00Z",
            "additions": 1,
            "deletions": 1,
            "labels": {"nodes": [{"name": "enhancement"}]},
            "milestone": {"title": "v1.0.0"},
            "author": _human,
        }
        bug = {
            "number": 2,
            "createdAt": "2025-04-01T10:00:00Z",
            "mergedAt": "2025-04-08T11:00:00Z",
            "additions": 1,
            "deletions": 1,
            "labels": {"nodes": [{"name": "bug"}]},
            "milestone": {"title": "v1.0.0"},
            "author": _human,
        }
        doc_pr = {
            "number": 3,
            "createdAt": "2025-04-01T10:00:00Z",
            "mergedAt": "2025-04-08T12:00:00Z",
            "additions": 1,
            "deletions": 1,
            "labels": {"nodes": [{"name": "documentation"}]},
            "milestone": {"title": "v1.0.0"},
            "author": _human,
        }

        mock_connector.post.side_effect = lambda path, payload: _graphql_page(
            [feat, bug, doc_pr]
        )
        # Next open v0.7.0 → include v0.5.1 + v0.6.0 closed + v0.7.0 open (sorted)
        mock_connector.get_paged.side_effect = [
            [{"title": "v0.7.0", "state": "open", "number": 3}],
            [
                {"title": "v0.5.0", "closed_at": "2025-01-01T00:00:00Z"},
                {"title": "v0.5.1", "closed_at": "2025-02-01T00:00:00Z"},
                {"title": "v0.6.0", "closed_at": "2025-03-01T00:00:00Z"},
            ],
        ]

        def get_side(path: str, headers=None):
            if "/search/issues" in path:
                # Escape issue on v0.6.0 counts toward previous milestone v0.5.1
                return {
                    "items": [
                        {
                            "milestone": {"title": "v0.6.0"},
                            "created_at": "2025-04-06T10:00:00Z",
                        }
                    ],
                    "total_count": 1,
                }
            raise AssertionError(path)

        mock_connector.get.side_effect = get_side

        async def override_conn():
            yield mock_connector

        with (
            patch("github_pm.sdlc_metrics.utc_now", return_value=fixed),
            patch("github_pm.sdlc_api.context") as ctx,
        ):
            ctx.github_repo = "test/repo"
            ctx.sdlc_feature_labels = "enhancement"
            ctx.sdlc_bug_labels = "bug"
            ctx.sdlc_docs_labels = "documentation"
            ctx.sdlc_escape_label = "escape"
            app.dependency_overrides[connection] = override_conn
            try:
                r = client.get("/api/v1/sdlc/escaped-defect-rate?weeks=1&week_days=7")
            finally:
                app.dependency_overrides.clear()

        assert r.status_code == 200
        data = r.json()
        assert data["weeks"] == 1
        assert len(data["slices"]) == 1
        slice0 = data["slices"][0]
        assert "as_of" in slice0
        body = slice0["releases"]
        assert len(body) == 3
        assert [r["release"] for r in body] == ["v0.5.1", "v0.6.0", "v0.7.0"]
        assert [r["is_next_open"] for r in body] == [False, False, True]
        assert body[0]["escape_issues"] == 1
        assert body[0]["docs_prs"] == 1
        assert body[0]["rate"] == pytest.approx(1.0 / 3.0)
        assert body[1]["escape_issues"] == 0
        assert body[1]["docs_prs"] == 1
        assert body[1]["rate"] == pytest.approx(0.0)
        assert body[2]["feature_prs"] == 1
        assert body[2]["bug_fix_prs"] == 1
        assert body[2]["docs_prs"] == 1
        assert body[2]["escape_issues"] == 0
        assert body[2]["rate"] == pytest.approx(0.0)


class TestBugBacklog:
    def test_bug_backlog_delta(self, client, mock_connector):
        opened_items = [
            {"created_at": "2025-04-05T10:00:00Z", "closed_at": None} for _ in range(4)
        ]
        closed_items = [
            {"created_at": "2025-03-01T00:00:00Z", "closed_at": "2025-04-06T10:00:00Z"}
        ]

        def get_side(path: str, headers=None):
            if "/search/issues" in path:
                if "is:closed" in path:
                    return {"items": closed_items, "total_count": len(closed_items)}
                return {"items": opened_items, "total_count": len(opened_items)}
            raise AssertionError(path)

        mock_connector.get.side_effect = get_side

        async def override_conn():
            yield mock_connector

        fixed = datetime(2025, 4, 10, 12, 0, 0, tzinfo=UTC)
        with (
            patch("github_pm.sdlc_metrics.utc_now", return_value=fixed),
            patch("github_pm.sdlc_api.context") as ctx,
        ):
            ctx.github_repo = "test/repo"
            ctx.sdlc_bug_labels = "bug"
            app.dependency_overrides[connection] = override_conn
            try:
                r = client.get("/api/v1/sdlc/bug-backlog-delta?weeks=1&week_days=7")
            finally:
                app.dependency_overrides.clear()

        assert r.status_code == 200
        d = r.json()
        assert d["weeks"] == 1
        assert len(d["slices"]) == 1
        s0 = d["slices"][0]
        assert s0["bugs_opened"] == 4
        assert s0["bugs_closed"] == 1
        assert s0["net"] == 3
