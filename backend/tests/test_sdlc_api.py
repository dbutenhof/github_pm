"""SDLC contracts, shared facts, interval boundaries and collection costs.

Generated-by: Codex
"""

from copy import deepcopy
from datetime import datetime, UTC
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest

from github_pm.api import connection
from github_pm.app import app
from github_pm.sdlc_service import compute_escaped_defect_rate

NOW = datetime(2025, 4, 10, 12, tzinfo=UTC)
SETTINGS = SimpleNamespace(
    sdlc_feature_labels="enhancement",
    sdlc_bug_labels="bug",
    sdlc_docs_labels="documentation",
    sdlc_escape_label="escape",
)


def page(nodes):
    return {
        "nodes": deepcopy(nodes),
        "issueCount": len(nodes),
        "pageInfo": {"hasNextPage": False, "endCursor": None},
    }


def pr(number, label, milestone="v0.1.0", **kwargs):
    return {
        "id": f"P{number}",
        "number": number,
        "__typename": "PullRequest",
        "createdAt": "2025-04-05T10:00:00Z",
        "mergedAt": "2025-04-06T10:00:00Z",
        "additions": 5,
        "deletions": 5,
        "labels": page([{"name": label}]),
        "milestone": {"title": milestone},
        "author": {"__typename": "User", "login": "contributor"},
        **kwargs,
    }


@pytest.fixture
def gitctx():
    client = MagicMock(owner="test", repo="repo")
    merged = [
        pr(1, "enhancement"),
        pr(2, "bug"),
        pr(3, "documentation"),
        pr(4, "enhancement", author={"__typename": "Bot", "login": "robot"}),
        pr(5, "enhancement", mergedAt="2025-04-03T12:00:00Z"),
    ]
    opened = [
        pr(
            10,
            "enhancement",
            mergedAt=None,
            reviews=page(
                [
                    {
                        "submittedAt": "2025-04-05T10:30:00Z",
                        "state": "COMMENTED",
                        "author": {"__typename": "Bot", "login": "bot"},
                    },
                    {
                        "submittedAt": "2025-04-05T12:00:00Z",
                        "state": "COMMENTED",
                        "author": {"__typename": "User", "login": "reviewer"},
                    },
                ]
            ),
        ),
        pr(11, "bug", mergedAt=None, reviews=page([])),
    ]
    escapes = [
        {
            "id": "E1",
            "number": 50,
            "createdAt": "2025-04-06T10:00:00Z",
            "milestone": {"title": "v0.2.0"},
        }
    ]
    bugs = [
        {"id": "B1", "number": 51, "createdAt": "2025-04-05T10:00:00Z"},
        {"id": "B2", "number": 52, "createdAt": "2025-04-10T12:00:00Z"},
        {"id": "B3", "number": 53, "createdAt": "2025-04-03T12:00:00Z"},
    ]
    closed = [
        {
            "id": "B4",
            "number": 54,
            "createdAt": "2020-01-01T00:00:00Z",
            "closedAt": "2025-04-06T10:00:00Z",
        }
    ]
    client.get_paged.return_value = [
        {
            "number": 1,
            "title": "v0.1.0",
            "state": "closed",
            "closed_at": "2025-01-01T00:00:00Z",
        },
        {"number": 2, "title": "v0.2.0", "state": "open"},
    ]

    def post(path, payload):
        assert path == "/graphql"
        data = {}
        for key, query in payload["variables"].items():
            if not key.startswith("q"):
                continue
            if "is:merged" in query:
                rows = merged
                if "milestone:" in query:
                    rows = [
                        n
                        for n in rows
                        if f'milestone:"{n["milestone"]["title"]}"' in query
                    ]
            elif "is:pr" in query:
                rows = opened
            elif "label:escape" in query:
                rows = escapes
            elif "is:closed" in query:
                rows = closed
            else:
                rows = bugs
            data["s" + key[1:]] = page(rows)
        return {"data": data}

    client.post.side_effect = post
    return client


@pytest.fixture
def client(gitctx):
    async def override():
        yield gitctx

    app.dependency_overrides[connection] = override
    with (
        patch("github_pm.sdlc_metrics.utc_now", return_value=NOW),
        patch("github_pm.sdlc_api.context", SETTINGS),
    ):
        yield TestClient(app)
    app.dependency_overrides.clear()


def test_delivery_preserves_bot_filter_review_selection_and_boundaries(client, gitctx):
    response = client.get("/api/v1/sdlc/delivery?weeks=1")
    assert response.status_code == 200, response.text
    slice0 = response.json()["slices"][0]
    assert slice0["merged_pr_throughput"]["total"] == 3
    assert slice0["merged_pr_throughput"]["by_pr_type"] == {
        "feature": 1,
        "bug_fix": 1,
        "docs": 1,
        "unclassified": 0,
    }
    assert slice0["median_pr_cycle_time"]["median_seconds"] == 86400
    assert slice0["median_time_to_first_review"]["median_seconds"] == 7200
    assert slice0["median_time_to_first_review"]["included_pr_count"] == 1
    assert slice0["median_time_to_first_review"]["eligible_pr_count"] == 2
    assert gitctx.post.call_count == 1
    gitctx.get.assert_not_called()
    gitctx.get_paged.assert_not_called()


def test_escape_preserves_release_attribution(client, gitctx):
    response = client.get("/api/v1/sdlc/escaped-defect-rate?weeks=1")
    assert response.status_code == 200, response.text
    rows = response.json()["slices"][0]["releases"]
    assert [r["release"] for r in rows] == ["v0.1.0", "v0.2.0"]
    assert rows[0]["escape_issues"] == 1
    assert rows[0]["docs_prs"] == 1
    assert rows[0]["rate"] == pytest.approx(1 / 3)
    assert rows[1]["is_next_open"] is True
    assert rows[1]["rate"] is None
    gitctx.get_paged.assert_called_once()
    assert "state=all" in gitctx.get_paged.call_args.args[0]


def test_bug_delta_includes_closures_of_older_issues_and_end_boundary(client):
    response = client.get("/api/v1/sdlc/bug-backlog-delta?weeks=1")
    assert response.status_code == 200, response.text
    row = response.json()["slices"][0]
    assert (row["bugs_opened"], row["bugs_closed"], row["net"]) == (2, 1, 1)


@pytest.mark.parametrize("weeks", [1, 4, 52])
def test_dashboard_fetches_facts_once_regardless_of_week_count(client, gitctx, weeks):
    response = client.get(f"/api/v1/sdlc/dashboard?weeks={weeks}")
    assert response.status_code == 200, response.text
    result = response.json()
    assert all(
        len(result[k]["slices"]) == weeks for k in ("delivery", "escaped", "backlog")
    )
    assert gitctx.post.call_count == 2  # Five independent searches in bounded batches.
    gitctx.get_paged.assert_called_once()
    gitctx.get.assert_not_called()
    queries = [
        v
        for call in gitctx.post.call_args_list
        for k, v in call.args[1]["variables"].items()
        if k.startswith("q")
    ]
    assert sum("is:merged" in q for q in queries) == 1
    assert all("milestone:" not in q for q in queries)
    assert len({result[k]["slices"][-1]["as_of"] for k in result}) == 1
    assert result["escaped"]["slices"][-1]["releases"][0]["rate"] == pytest.approx(
        1 / 3
    )


def test_weekly_boundary_is_counted_once(client):
    response = client.get("/api/v1/sdlc/dashboard?weeks=2")
    result = response.json()
    assert [
        s["merged_pr_throughput"]["total"] for s in result["delivery"]["slices"]
    ] == [1, 3]
    assert [s["bugs_opened"] for s in result["backlog"]["slices"]] == [1, 2]


def test_cumulative_escape_keeps_historical_scope(gitctx):
    with patch("github_pm.sdlc_metrics.utc_now", return_value=NOW):
        result = compute_escaped_defect_rate(gitctx, SETTINGS)
    assert result.window_start is None
    assert result.releases[0].feature_prs == 2
    assert result.releases[0].rate == pytest.approx(1 / 4)


def test_dashboard_rejects_partial_github_data(client, gitctx):
    gitctx.post.side_effect = None
    gitctx.post.return_value = {
        "data": {},
        "errors": [{"message": "permission denied"}],
    }
    with pytest.raises(RuntimeError, match="permission denied"):
        client.get("/api/v1/sdlc/dashboard")
