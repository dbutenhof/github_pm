"""Small GitHub projections and independent, complete connection pagination.

Generated-by: Codex
"""

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, UTC
import re
from urllib.parse import urlencode

from github_pm.context import _parse_sdlc_label_csv

PAGE = "pageInfo { hasNextPage endCursor }"
AUTHOR = "author { __typename login }"
LABELS = "labels(first:100) { nodes { name } " + PAGE + " }"
REVIEWS = (
    "reviews(first:100) { nodes { submittedAt state " + AUTHOR + " } " + PAGE + " }"
)
SUMMARY = "id number title url createdAt updatedAt state isDraft mergedAt"
DELIVERY = (
    "id number createdAt mergedAt additions deletions milestone { title } "
    + AUTHOR
    + " "
    + LABELS
)
ESCAPE = "id number mergedAt milestone { title } " + AUTHOR + " " + LABELS
ATTENTION = SUMMARY + " mergeable mergeStateStatus " + REVIEWS
ISSUE_DATES = "id number createdAt closedAt milestone { title }"


def execute(post, query, variables=None):
    result = post({"query": query, "variables": variables or {}})
    if result.get("errors"):
        messages = "; ".join(str(e.get("message", e)) for e in result["errors"])
        raise RuntimeError(f"GitHub GraphQL error: {messages}")
    data = result.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("GitHub GraphQL response is missing data")
    return data


def next_cursor(connection, previous=None):
    if not isinstance(connection.get("nodes"), list):
        raise RuntimeError("GitHub connection is missing its nodes")
    page = connection.get("pageInfo")
    if not isinstance(page, dict):
        raise RuntimeError("GitHub connection is missing pagination information")
    if not page.get("hasNextPage"):
        return None
    cursor = page.get("endCursor")
    if not cursor or cursor == previous:
        raise RuntimeError("GitHub pagination failed to advance")
    return cursor


@dataclass(frozen=True)
class Search:
    query: str
    fields: str
    typename: str = "PullRequest"


def _split_query(query):
    match = re.search(r"\b(created|merged|closed):([^\s]+)\.\.([^\s]+)", query)
    if not match:
        raise RuntimeError(
            "GitHub search exceeds 1,000 results; a bounded date interval is required"
        )
    field, lo, hi = match.groups()
    start = datetime.fromisoformat(lo.replace("Z", "+00:00")).replace(tzinfo=UTC)
    end = datetime.fromisoformat(hi.replace("Z", "+00:00")).replace(tzinfo=UTC)
    if len(hi) == 10:
        end += timedelta(days=1, seconds=-1)
    seconds = int((end - start).total_seconds())
    if seconds < 1:
        raise RuntimeError(
            "More than 1,000 GitHub search matches in a single second; results would be incomplete"
        )
    midpoint = start + timedelta(seconds=seconds // 2)

    def ranged(a, b):
        token = f'{field}:{a.strftime("%Y-%m-%dT%H:%M:%SZ")}..{b.strftime("%Y-%m-%dT%H:%M:%SZ")}'
        return query[: match.start()] + token + query[match.end() :]

    return ranged(start, midpoint), ranged(midpoint + timedelta(seconds=1), end)


def search_many(post, searches):
    """Batch independent searches, splitting large intervals before collecting pages."""
    results = {key: [] for key in searches}
    pending = [(key, spec, None) for key, spec in searches.items()]
    visited = set()
    while pending:
        batch, pending = pending[:4], pending[4:]
        definitions, fields, variables = [], [], {}
        for i, (key, spec, cursor) in enumerate(batch):
            marker = (key, spec.query, cursor)
            if marker in visited:
                raise RuntimeError("GitHub search pagination repeated a cursor")
            visited.add(marker)
            definitions.extend([f"$q{i}:String!", f"$c{i}:String"])
            variables.update({f"q{i}": spec.query, f"c{i}": cursor})
            fields.append(
                f"s{i}:search(query:$q{i}, type:ISSUE, first:100, after:$c{i}) {{ issueCount {PAGE} nodes {{ __typename ... on {spec.typename} {{ {spec.fields} }} }} }}"
            )
        data = execute(
            post,
            "query("
            + ",".join(definitions)
            + ") { "
            + " ".join(fields)
            + " rateLimit { cost } }",
            variables,
        )
        for i, (key, spec, cursor) in enumerate(batch):
            connection = data.get(f"s{i}")
            if not isinstance(connection, dict):
                raise RuntimeError(f"GitHub search {key} is missing")
            if not isinstance(connection.get("issueCount"), int):
                raise RuntimeError("GitHub search omitted the result count")
            if connection["issueCount"] > 1000:
                if cursor:
                    raise RuntimeError(
                        "GitHub search changed during pagination; retry the report"
                    )
                pending.extend(
                    (key, replace(spec, query=q), None)
                    for q in _split_query(spec.query)
                )
                continue
            results[key].extend(
                n
                for n in connection.get("nodes", [])
                if n and n.get("number") is not None
            )
            after = next_cursor(connection, cursor)
            if after:
                pending.append((key, spec, after))
    for key, nodes in results.items():
        results[key] = list(
            {
                n.get("id") or (n.get("__typename"), n["number"]): n for n in nodes
            }.values()
        )
    return results


def complete_connections(post, nodes, typename, connections):
    """Finish nested connections in bounded batches with an independent cursor per node/field.

    connections maps field names to (node selection, additional arguments).
    """
    pending = []
    visited = set()
    for node in nodes:
        for field, (selection, extra) in connections.items():
            connection = node.get(field)
            if connection is None:
                raise RuntimeError(
                    f'GitHub omitted {field} for #{node.get("number", "?")}'
                )
            cursor = next_cursor(connection)
            if cursor:
                if not node.get("id"):
                    raise RuntimeError(
                        "GitHub omitted the node ID needed for pagination"
                    )
                pending.append((node, field, selection, extra, cursor))
    while pending:
        batch, pending = pending[:25], pending[25:]
        definitions, fields, variables = [], [], {}
        for i, (node, field, selection, extra, cursor) in enumerate(batch):
            marker = (node["id"], field, cursor)
            if marker in visited:
                raise RuntimeError("GitHub nested pagination repeated a cursor")
            visited.add(marker)
            definitions.extend([f"$id{i}:ID!", f"$c{i}:String!"])
            variables.update({f"id{i}": node["id"], f"c{i}": cursor})
            args = f"first:100,after:$c{i}" + ("," + extra if extra else "")
            fields.append(
                f"n{i}:node(id:$id{i}) {{ ... on {typename} {{ {field}({args}) {{ nodes {{ {selection} }} {PAGE} }} }} }}"
            )
        data = execute(
            post,
            "query("
            + ",".join(definitions)
            + ") { "
            + " ".join(fields)
            + " rateLimit { cost } }",
            variables,
        )
        for i, (node, field, selection, extra, cursor) in enumerate(batch):
            connection = (data.get(f"n{i}") or {}).get(field)
            if not isinstance(connection, dict):
                raise RuntimeError(f"GitHub omitted a continuation for {field}")
            node[field]["nodes"].extend(connection.get("nodes") or [])
            node[field]["pageInfo"] = connection["pageInfo"]
            after = next_cursor(connection, cursor)
            if after:
                pending.append((node, field, selection, extra, after))


def complete_prs(post, nodes, *, labels=False, reviews=False):
    connections = {}
    if labels:
        connections["labels"] = ("name", "")
    if reviews:
        connections["reviews"] = ("submittedAt state " + AUTHOR, "")
    complete_connections(post, nodes, "PullRequest", connections)
    return nodes


def open_prs(post, owner, repo):
    nodes, cursor, visited = [], None, set()
    while True:
        if cursor in visited:
            raise RuntimeError("GitHub open PR pagination repeated a cursor")
        visited.add(cursor)
        data = execute(
            post,
            "query($owner:String!,$repo:String!,$cursor:String) { repository(owner:$owner,name:$repo) { pullRequests(states:[OPEN],first:100,after:$cursor) { nodes { "
            + ATTENTION
            + " } "
            + PAGE
            + " } } rateLimit { cost } }",
            {"owner": owner, "repo": repo, "cursor": cursor},
        )
        connection = (data.get("repository") or {}).get("pullRequests")
        if not isinstance(connection, dict):
            raise RuntimeError("GitHub omitted the open pull request collection")
        nodes.extend(n for n in connection.get("nodes") or [] if n)
        cursor = next_cursor(connection, cursor)
        if not cursor:
            break
    return complete_prs(post, nodes, reviews=True)


def rest_search(get, query):
    """Complete REST searches, including explicit oversized/incomplete-result handling."""
    items, page = [], 1
    while True:
        data = get(
            "/search/issues?" + urlencode({"q": query, "per_page": 100, "page": page})
        )
        if data.get("incomplete_results"):
            raise RuntimeError(
                "GitHub search returned incomplete results; retry the report"
            )
        if data.get("total_count", 0) > 1000:
            if page != 1:
                raise RuntimeError(
                    "GitHub search changed during pagination; retry the report"
                )
            partitions = _split_query(query)
            return list(
                {
                    item["id"]: item
                    for part in partitions
                    for item in rest_search(get, part)
                }.values()
            )
        batch = data.get("items") or []
        items.extend(batch)
        total = data.get("total_count")
        if not isinstance(total, int):
            raise RuntimeError("GitHub search omitted the result count")
        if len(items) >= total:
            return list({item["id"]: item for item in items}.values())
        if not batch:
            raise RuntimeError("GitHub search ended before returning all matches")
        page += 1


def date_str(d: datetime) -> str:
    """GitHub search date (YYYY-MM-DD) in UTC."""
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return d.astimezone(UTC).date().isoformat()


def escape_labeled_issues_query(github_repo: str, escape_label: str) -> str:
    """GitHub issue search query for issues carrying the escape label."""
    lab = escape_label.strip().lower()
    if not lab:
        lab = "escape"
    label_tok = f'label:"{lab}"' if any(c in lab for c in " /") else f"label:{lab}"
    return f"{repo_search_fragment(github_repo)} is:issue {label_tok}"


def repo_search_fragment(github_repo: str) -> str:
    return f"repo:{github_repo}"


def merged_prs_query(github_repo: str, merged_since: datetime) -> str:
    return (
        f"{repo_search_fragment(github_repo)} is:pr is:merged "
        f"merged:>={date_str(merged_since)}"
    )


def merged_prs_query_between(github_repo: str, start_d: date, end_d: date) -> str:
    """GraphQL issue search: merged PRs with merge date in ``[start_d, end_d]`` (UTC calendar days).

    REST ``GET /search/issues`` rejects several merged/closed date combinations (422); GraphQL
    ``search`` accepts ``merged:`` ranges the same way as the web UI.
    """
    a, b = start_d.isoformat(), end_d.isoformat()
    if a > b:
        a, b = b, a
    return f"{repo_search_fragment(github_repo)} is:pr is:merged merged:{a}..{b}"


def opened_prs_between_query(github_repo: str, start_d: date, end_d: date) -> str:
    """PRs with ``created`` in ``[start_d, end_d]`` (UTC calendar days, inclusive)."""
    a, b = start_d.isoformat(), end_d.isoformat()
    if a > b:
        a, b = b, a
    return f"{repo_search_fragment(github_repo)} is:pr created:{a}..{b}"


def open_pr_backlog_query(github_repo: str, start_d: date) -> str:
    """Open, non-draft PRs last updated strictly before ``start_d`` (UTC calendar day at 00:00).

    Uses ``draft:false`` and ``updated:<YYYY-MM-DD``; callers should still verify
    ``updatedAt`` in UTC against ``start_d`` and ``isDraft`` for edge cases.
    """
    d = start_d.isoformat()
    return f"{repo_search_fragment(github_repo)} is:pr is:open draft:false updated:<{d}"


def open_pull_requests_for_attention_query(github_repo: str) -> str:
    """All open pull requests in the repo (drafts included) for merge/review heuristics."""
    return f"{repo_search_fragment(github_repo)} is:pr is:open"


def open_prs_updated_between_query(github_repo: str, start_d: date, end_d: date) -> str:
    """Open, non-draft PRs with ``updated`` in ``[start_d, end_d]`` (UTC calendar days, inclusive)."""
    a, b = start_d.isoformat(), end_d.isoformat()
    if a > b:
        a, b = b, a
    return (
        f"{repo_search_fragment(github_repo)} is:pr is:open draft:false "
        f"updated:{a}..{b}"
    )


def opened_issues_between_query(github_repo: str, start_d: date, end_d: date) -> str:
    """Issues (not PRs) with ``created`` in ``[start_d, end_d]`` (UTC calendar days, inclusive)."""
    a, b = start_d.isoformat(), end_d.isoformat()
    if a > b:
        a, b = b, a
    return f"{repo_search_fragment(github_repo)} is:issue created:{a}..{b}"


def opened_prs_query(github_repo: str, created_since: datetime) -> str:
    return (
        f"{repo_search_fragment(github_repo)} is:pr "
        f"created:>={date_str(created_since)}"
    )


def milestone_merged_prs_query(github_repo: str, milestone_title: str) -> str:
    # Quote milestone title for spaces/special chars
    safe = milestone_title.replace('"', "\\")
    return f'{repo_search_fragment(github_repo)} is:pr is:merged milestone:"{safe}"'


def bug_issues_created_query(
    github_repo: str, bug_labels_csv: str, since: datetime
) -> str:
    """Issues with bug label(s) created on or after `since` (any state)."""
    label_clause = _label_or_clause(_parse_sdlc_label_csv(bug_labels_csv))
    return (
        f"{repo_search_fragment(github_repo)} is:issue {label_clause} "
        f"created:>={date_str(since)}"
    )


def bug_issues_closed_query(
    github_repo: str, bug_labels_csv: str, since: datetime
) -> str:
    label_clause = _label_or_clause(_parse_sdlc_label_csv(bug_labels_csv))
    return (
        f"{repo_search_fragment(github_repo)} is:issue is:closed {label_clause} "
        f"closed:>={date_str(since)}"
    )


def bug_issues_created_query_between(
    github_repo: str, bug_labels_csv: str, lo: datetime, hi: datetime
) -> str:
    """Bug issues created with ``created`` in ``[date(lo), date(hi)]`` (UTC dates, inclusive)."""
    label_clause = _label_or_clause(_parse_sdlc_label_csv(bug_labels_csv))
    a, b = date_str(lo), date_str(hi)
    if a > b:
        a, b = b, a
    return (
        f"{repo_search_fragment(github_repo)} is:issue {label_clause} created:{a}..{b}"
    )


def bug_issues_closed_query_between(
    github_repo: str, bug_labels_csv: str, lo: datetime, hi: datetime
) -> str:
    """Closed bug issues with ``closed`` in ``[date(lo), date(hi)]`` (UTC dates, inclusive)."""
    label_clause = _label_or_clause(_parse_sdlc_label_csv(bug_labels_csv))
    a, b = date_str(lo), date_str(hi)
    if a > b:
        a, b = b, a
    return (
        f"{repo_search_fragment(github_repo)} is:issue is:closed {label_clause} "
        f"closed:{a}..{b}"
    )


def _label_or_clause(labels: frozenset[str]) -> str:
    if not labels:
        return ""
    parts = [
        f'label:"{lab}"' if any(c in lab for c in " /") else f"label:{lab}"
        for lab in sorted(labels)
    ]
    if len(parts) == 1:
        return parts[0]
    return "(" + " OR ".join(parts) + ")"
