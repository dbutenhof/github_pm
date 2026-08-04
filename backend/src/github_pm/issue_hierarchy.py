"""Build and mutate GitHub sub-issue hierarchies for the planner.

Generated-by: Cursor
"""

from __future__ import annotations

from typing import Any, Callable

from github_pm.logger import logger

SortFn = Callable[[list[dict], list[str]], list[dict]]


def _external_parent_payload(parent: dict[str, Any] | None) -> dict[str, Any] | None:
    """Normalize a GraphQL parent node into the API's external_parent shape."""
    if not parent or parent.get("number") is None:
        return None
    milestone = parent.get("milestone")
    return {
        "number": parent["number"],
        "title": parent.get("title"),
        "milestone": (
            {
                "number": milestone.get("number"),
                "title": milestone.get("title"),
            }
            if isinstance(milestone, dict)
            else None
        ),
    }


def _would_create_cycle(
    child_number: int,
    parent_number: int,
    parent_of: dict[int, int],
) -> bool:
    """Return True if linking child under parent would create a cycle."""
    if child_number == parent_number:
        return True
    current: int | None = parent_number
    seen: set[int] = set()
    while current is not None:
        if current == child_number:
            return True
        if current in seen:
            break
        seen.add(current)
        current = parent_of.get(current)
    return False


def build_issue_forest(
    issues: list[dict],
    sort_by: list[str],
    sort_fn: SortFn,
) -> list[dict]:
    """Nest open milestone issues into a forest using GraphQL parent links.

    Issues whose parent is outside this open set become display roots with
    ``external_parent`` set. Cyclic edges are broken by treating them as
    external/orphan roots.

    Assisted-by: Cursor
    """
    by_number: dict[int, dict] = {}
    for issue in issues:
        node = dict(issue)
        node["children"] = []
        node["parent_number"] = None
        node["external_parent"] = None
        node["hierarchy_depth"] = 0
        node["child_count"] = 0
        by_number[node["number"]] = node

    # Proposed in-tree edges: child -> parent when parent is in this set.
    parent_of: dict[int, int] = {}
    external: dict[int, dict[str, Any]] = {}

    for number, node in by_number.items():
        parent_info = node.get("_parent_info")
        if not parent_info or parent_info.get("number") is None:
            continue
        parent_number = parent_info["number"]
        if parent_number in by_number:
            parent_of[number] = parent_number
        else:
            external[number] = _external_parent_payload(parent_info)

    # Drop cyclic edges.
    for child, parent in list(parent_of.items()):
        if _would_create_cycle(
            child, parent, {k: v for k, v in parent_of.items() if k != child}
        ):
            logger.warning("Breaking cyclic sub-issue edge #%s -> #%s", child, parent)
            parent_info = by_number[child].get("_parent_info")
            external[child] = _external_parent_payload(parent_info) or {
                "number": parent,
                "title": None,
                "milestone": None,
            }
            del parent_of[child]

    children_map: dict[int, list[int]] = {n: [] for n in by_number}
    for child, parent in parent_of.items():
        children_map[parent].append(child)
        by_number[child]["parent_number"] = parent

    for number, payload in external.items():
        by_number[number]["external_parent"] = payload

    def attach(number: int, depth: int) -> dict:
        node = by_number[number]
        node["hierarchy_depth"] = depth
        child_nodes = [attach(c, depth + 1) for c in children_map[number]]
        node["children"] = sort_fn(child_nodes, sort_by)
        node["child_count"] = len(node["children"])
        # Strip internal enrichment key before returning.
        node.pop("_parent_info", None)
        return node

    roots = [number for number in by_number if number not in parent_of]
    forest = [attach(n, 0) for n in roots]
    return sort_fn(forest, sort_by)


def apply_graphql_hierarchy(issue: dict, issue_node: dict | None) -> None:
    """Attach parent / sub-issue summary fields from a GraphQL issue node.

    Generated-by: Cursor
    """
    if not issue_node:
        return
    parent = issue_node.get("parent")
    if parent:
        issue["_parent_info"] = {
            "number": parent.get("number"),
            "title": parent.get("title"),
            "milestone": parent.get("milestone"),
        }
    summary = issue_node.get("subIssuesSummary")
    if summary:
        issue["sub_issues_summary"] = {
            "total": summary.get("total", 0),
            "completed": summary.get("completed", 0),
            "percent_completed": summary.get("percentCompleted", 0),
        }


def _dependency_nodes(connection: dict | None) -> list[dict]:
    """Map GraphQL blockedBy/blocking connection nodes to API payloads.

    Generated-by: Cursor
    """
    nodes = (connection or {}).get("nodes") or []
    return [
        {
            "id": linked.get("databaseId"),
            "number": linked["number"],
            "title": linked.get("title"),
            "url": linked.get("url"),
            "state": linked.get("state"),
        }
        for linked in nodes
        if linked.get("number") is not None
    ]


def apply_graphql_links(issue: dict, issue_node: dict | None) -> None:
    """Attach closed-by PRs and blocked-by / blocking issue links from GraphQL.

    Generated-by: Cursor
    """
    if not issue_node:
        return
    closed_refs = issue_node.get("closedByPullRequestsReferences") or {}
    closed = closed_refs.get("nodes") or []
    if closed:
        issue["closed_by"] = [
            {
                "number": linked["number"],
                "title": linked.get("title"),
                "url": linked.get("url"),
            }
            for linked in closed
        ]
    blocked_by = _dependency_nodes(issue_node.get("blockedBy"))
    if blocked_by:
        issue["blocked_by"] = blocked_by
    blocking = _dependency_nodes(issue_node.get("blocking"))
    if blocking:
        issue["blocking"] = blocking


ISSUE_HIERARCHY_GRAPHQL = """
query($owner: String!, $repo: String!, $issue: Int!) {
    repository(owner: $owner, name: $repo, followRenames: true) {
        issue(number: $issue) {
            closedByPullRequestsReferences(first: 100, includeClosedPrs: true) {
                nodes {
                    number
                    title
                    url
                }
            }
            blockedBy(first: 50) {
                nodes {
                    databaseId
                    number
                    title
                    url
                    state
                }
            }
            blocking(first: 50) {
                nodes {
                    databaseId
                    number
                    title
                    url
                    state
                }
            }
            parent {
                number
                title
                milestone {
                    number
                    title
                }
            }
            subIssues(first: 100) {
                nodes {
                    number
                }
            }
            subIssuesSummary {
                total
                completed
                percentCompleted
            }
        }
    }
}
"""

PARENT_ONLY_GRAPHQL = """
query($owner: String!, $repo: String!, $issue: Int!) {
    repository(owner: $owner, name: $repo, followRenames: true) {
        issue(number: $issue) {
            id
            number
            parent {
                number
                title
                milestone {
                    number
                    title
                }
            }
            subIssues(first: 100) {
                nodes {
                    number
                }
            }
        }
    }
}
"""


def collect_descendant_numbers(
    list_sub_issues: Callable[[int], list[int]],
    root_number: int,
) -> list[int]:
    """BFS over GitHub sub-issues starting at root (excluding root itself).

    Generated-by: Cursor
    """
    descendants: list[int] = []
    queue = list(list_sub_issues(root_number))
    seen: set[int] = {root_number}
    while queue:
        number = queue.pop(0)
        if number in seen:
            continue
        seen.add(number)
        descendants.append(number)
        queue.extend(list_sub_issues(number))
    return descendants


def is_ancestor(
    list_sub_issues: Callable[[int], list[int]],
    ancestor_number: int,
    descendant_number: int,
) -> bool:
    """True if ancestor_number is an ancestor of descendant_number via sub-issues."""
    if ancestor_number == descendant_number:
        return True
    return descendant_number in collect_descendant_numbers(
        list_sub_issues, ancestor_number
    )
