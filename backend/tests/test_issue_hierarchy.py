"""Tests for issue hierarchy forest building.

Generated-by: Cursor
"""

from github_pm.api import _sort_items_by_labels
from github_pm.issue_hierarchy import (
    apply_graphql_hierarchy,
    apply_graphql_links,
    build_issue_forest,
    collect_descendant_numbers,
    is_ancestor,
)


def _issue(number: int, labels=None, parent=None, **extra):
    item = {
        "id": number * 10,
        "number": number,
        "title": f"Issue {number}",
        "labels": labels or [],
        **extra,
    }
    if parent is not None:
        item["_parent_info"] = parent
    return item


class TestBuildIssueForest:
    def test_flat_peers_are_epics(self):
        issues = [_issue(1), _issue(2), _issue(3)]
        forest = build_issue_forest(issues, [], _sort_items_by_labels)
        assert [n["number"] for n in forest] == [1, 2, 3]
        for node in forest:
            assert node["hierarchy_depth"] == 0
            assert node["parent_number"] is None
            assert node["external_parent"] is None
            assert node["children"] == []
            assert node["child_count"] == 0

    def test_nests_when_parent_in_set(self):
        issues = [
            _issue(1),
            _issue(2, parent={"number": 1, "title": "Epic", "milestone": None}),
            _issue(3, parent={"number": 2, "title": "Story", "milestone": None}),
        ]
        forest = build_issue_forest(issues, [], _sort_items_by_labels)
        assert len(forest) == 1
        epic = forest[0]
        assert epic["number"] == 1
        assert epic["hierarchy_depth"] == 0
        assert epic["child_count"] == 1
        story = epic["children"][0]
        assert story["number"] == 2
        assert story["hierarchy_depth"] == 1
        assert story["parent_number"] == 1
        substory = story["children"][0]
        assert substory["number"] == 3
        assert substory["hierarchy_depth"] == 2
        assert substory["parent_number"] == 2

    def test_external_parent_becomes_root(self):
        issues = [
            _issue(
                5,
                parent={
                    "number": 99,
                    "title": "Other Epic",
                    "milestone": {"number": 7, "title": "v1"},
                },
            )
        ]
        forest = build_issue_forest(issues, [], _sort_items_by_labels)
        assert len(forest) == 1
        node = forest[0]
        assert node["number"] == 5
        assert node["hierarchy_depth"] == 0
        assert node["parent_number"] is None
        assert node["external_parent"] == {
            "number": 99,
            "title": "Other Epic",
            "milestone": {"number": 7, "title": "v1"},
        }

    def test_breaks_cycles(self):
        issues = [
            _issue(1, parent={"number": 2, "title": "B", "milestone": None}),
            _issue(2, parent={"number": 1, "title": "A", "milestone": None}),
        ]
        forest = build_issue_forest(issues, [], _sort_items_by_labels)
        # One edge breaks; both should appear as roots (or one nested).
        numbers = {n["number"] for n in forest}
        assert numbers == {1, 2} or (len(forest) == 1 and forest[0]["child_count"] == 1)
        # No infinite nesting: depths finite and children don't loop.
        for root in forest:
            assert root["hierarchy_depth"] == 0

    def test_label_sort_within_siblings(self):
        issues = [
            _issue(1),
            _issue(
                3,
                labels=[{"name": "bug"}],
                parent={"number": 1, "title": "E", "milestone": None},
            ),
            _issue(
                2,
                labels=[{"name": "feature"}],
                parent={"number": 1, "title": "E", "milestone": None},
            ),
            _issue(4, labels=[{"name": "bug"}]),
            _issue(5, labels=[{"name": "feature"}]),
        ]
        forest = build_issue_forest(issues, ["bug", "feature"], _sort_items_by_labels)
        # Roots: 4 (bug), 5 (feature), 1 (other, with children)
        assert [n["number"] for n in forest] == [4, 5, 1]
        children = forest[2]["children"]
        assert [c["number"] for c in children] == [3, 2]

    def test_strips_internal_parent_info(self):
        issues = [
            _issue(1, parent={"number": 99, "title": "X", "milestone": None}),
        ]
        forest = build_issue_forest(issues, [], _sort_items_by_labels)
        assert "_parent_info" not in forest[0]


class TestApplyGraphqlHierarchy:
    def test_applies_parent_and_summary(self):
        issue = {"number": 1}
        apply_graphql_hierarchy(
            issue,
            {
                "parent": {
                    "number": 2,
                    "title": "P",
                    "milestone": {"number": 3, "title": "M"},
                },
                "subIssuesSummary": {
                    "total": 4,
                    "completed": 1,
                    "percentCompleted": 25,
                },
            },
        )
        assert issue["_parent_info"]["number"] == 2
        assert issue["sub_issues_summary"]["total"] == 4
        assert issue["sub_issues_summary"]["percent_completed"] == 25


class TestApplyGraphqlLinks:
    def test_applies_closed_by_and_dependencies(self):
        issue = {"number": 1}
        apply_graphql_links(
            issue,
            {
                "closedByPullRequestsReferences": {
                    "nodes": [
                        {
                            "number": 9,
                            "title": "PR",
                            "url": "https://example.com/pull/9",
                        }
                    ]
                },
                "blockedBy": {
                    "nodes": [
                        {
                            "databaseId": 100,
                            "number": 2,
                            "title": "Blocker",
                            "url": "https://example.com/issues/2",
                            "state": "OPEN",
                        }
                    ]
                },
                "blocking": {
                    "nodes": [
                        {
                            "databaseId": 200,
                            "number": 3,
                            "title": "Blocked",
                            "url": "https://example.com/issues/3",
                            "state": "CLOSED",
                        }
                    ]
                },
            },
        )
        assert issue["closed_by"] == [
            {
                "number": 9,
                "title": "PR",
                "url": "https://example.com/pull/9",
            }
        ]
        assert issue["blocked_by"] == [
            {
                "id": 100,
                "number": 2,
                "title": "Blocker",
                "url": "https://example.com/issues/2",
                "state": "OPEN",
            }
        ]
        assert issue["blocking"] == [
            {
                "id": 200,
                "number": 3,
                "title": "Blocked",
                "url": "https://example.com/issues/3",
                "state": "CLOSED",
            }
        ]

    def test_omits_empty_link_collections(self):
        issue = {"number": 1}
        apply_graphql_links(
            issue,
            {
                "closedByPullRequestsReferences": {"nodes": []},
                "blockedBy": {"nodes": []},
                "blocking": None,
            },
        )
        assert "closed_by" not in issue
        assert "blocked_by" not in issue
        assert "blocking" not in issue


class TestCollectDescendants:
    def test_bfs_descendants(self):
        tree = {1: [2, 3], 2: [4], 3: [], 4: []}

        def list_children(n):
            return tree.get(n, [])

        assert collect_descendant_numbers(list_children, 1) == [2, 3, 4]
        assert is_ancestor(list_children, 1, 4) is True
        assert is_ancestor(list_children, 2, 3) is False
        assert is_ancestor(list_children, 1, 1) is True
