"""Complete, bounded collection across independent roots and nested connections.

Generated-by: Codex
"""

from unittest.mock import Mock

import pytest

from github_pm import report_queries as rq


def page(nodes, cursor=None, count=None):
    return {
        "nodes": nodes,
        "pageInfo": {"hasNextPage": bool(cursor), "endCursor": cursor},
        "issueCount": count if count is not None else len(nodes),
    }


def node(number):
    return {"id": f"P{number}", "number": number, "__typename": "PullRequest"}


def test_independent_root_cursors_and_stable_deduplication():
    post = Mock(
        side_effect=[
            {"data": {"s0": page([node(1)], "a"), "s1": page([node(2)])}},
            {"data": {"s0": page([node(1), node(3)])}},
        ]
    )
    result = rq.search_many(
        post, {"a": rq.Search("a", "id number"), "b": rq.Search("b", "id number")}
    )
    assert [n["number"] for n in result["a"]] == [1, 3]
    assert [n["number"] for n in result["b"]] == [2]
    assert post.call_args.args[0]["variables"] == {"q0": "a", "c0": "a"}


def test_oversized_search_partitions_dates_before_collecting():
    post = Mock(
        side_effect=[
            {"data": {"s0": page([node(9999)], count=1501)}},
            {"data": {"s0": page([node(1)]), "s1": page([node(2)])}},
        ]
    )
    result = rq.search_many(
        post,
        {"a": rq.Search("repo:a/b is:pr merged:2025-04-01..2025-04-02", "id number")},
    )
    assert [n["number"] for n in result["a"]] == [1, 2]
    variables = post.call_args.args[0]["variables"]
    assert "merged:2025-04-01T00:00:00Z..2025-04-01T23:59:59Z" in variables["q0"]
    assert "merged:2025-04-02T00:00:00Z..2025-04-02T23:59:59Z" in variables["q1"]


def test_single_second_overflow_is_explicit():
    post = Mock(return_value={"data": {"s0": page([], count=1001)}})
    with pytest.raises(RuntimeError, match="single second"):
        rq.search_many(
            post,
            {
                "a": rq.Search(
                    "created:2025-01-01T00:00:00Z..2025-01-01T00:00:00Z", "id number"
                )
            },
        )


def test_nested_reviews_and_labels_use_independent_cursors():
    nodes = [
        dict(
            node(1),
            reviews=page(
                [{"state": "COMMENTED", "author": {"__typename": "Bot"}}], "r1"
            ),
            labels=page([], "l1"),
        ),
        dict(node(2), reviews=page([], "r2"), labels=page([])),
    ]
    post = Mock(
        return_value={
            "data": {
                "n0": {"labels": page([{"name": "bug"}])},
                "n1": {
                    "reviews": page(
                        [{"state": "APPROVED", "author": {"login": "alice"}}]
                    )
                },
                "n2": {
                    "reviews": page([{"state": "APPROVED", "author": {"login": "bob"}}])
                },
            }
        }
    )
    rq.complete_prs(post, nodes, labels=True, reviews=True)
    assert nodes[0]["labels"]["nodes"] == [{"name": "bug"}]
    assert len(nodes[0]["reviews"]["nodes"]) == 2
    assert nodes[1]["reviews"]["nodes"][0]["author"]["login"] == "bob"
    assert post.call_args.args[0]["variables"] == {
        "id0": "P1",
        "c0": "l1",
        "id1": "P1",
        "c1": "r1",
        "id2": "P2",
        "c2": "r2",
    }


def test_repeated_nested_cursor_fails_instead_of_looping():
    nodes = [dict(node(1), reviews=page([], "same"))]
    post = Mock(return_value={"data": {"n0": {"reviews": page([], "same")}}})
    with pytest.raises(RuntimeError, match="failed to advance"):
        rq.complete_prs(post, nodes, reviews=True)
    assert post.call_count == 1


def test_open_repository_connection_has_no_search_cap_and_completes_reviews():
    nodes = [dict(node(i), reviews=page([])) for i in range(1001)]
    post = Mock(
        side_effect=[
            {"data": {"repository": {"pullRequests": page(nodes[:1000], "more")}}},
            {"data": {"repository": {"pullRequests": page(nodes[1000:])}}},
        ]
    )
    assert len(rq.open_prs(post, "a", "b")) == 1001
    assert post.call_args.args[0]["variables"]["cursor"] == "more"
    assert "search(" not in post.call_args.args[0]["query"]


@pytest.mark.parametrize(
    "result", [{"errors": [{"message": "denied"}], "data": {}}, {"data": None}]
)
def test_partial_graphql_data_is_not_a_successful_empty_report(result):
    with pytest.raises(RuntimeError):
        rq.execute(lambda _: result, "query { viewer { login } }")


def test_rest_search_paginates_and_rejects_incomplete_results():
    get = Mock(
        side_effect=[
            {"items": [{"id": i} for i in range(100)], "total_count": 101},
            {"items": [{"id": 100}], "total_count": 101},
        ]
    )
    assert len(rq.rest_search(get, "repo:a/b")) == 101
    assert "per_page=100&page=2" in get.call_args.args[0]
    with pytest.raises(RuntimeError, match="incomplete"):
        rq.rest_search(lambda _: {"incomplete_results": True}, "repo:a/b")
