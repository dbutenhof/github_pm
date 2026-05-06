"""SDLC KPI helpers: PR classification, size buckets, medians, GitHub search."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import datetime, timedelta, UTC
import re
from typing import Any, Literal
from urllib.parse import quote_plus

from github_pm.context import _parse_sdlc_label_csv, Settings
from github_pm.logger import logger

PRType = Literal["feature", "bug_fix", "docs", "unclassified"]
SizeBucket = Literal["tiny", "small", "medium", "large", "unknown"]


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def window_start(days: int, now: datetime | None = None) -> datetime:
    """Start of rolling window: `now - days`, UTC."""
    if now is None:
        now = utc_now()
    return now - timedelta(days=days)


def date_str(d: datetime) -> str:
    """GitHub search date (YYYY-MM-DD) in UTC."""
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return d.astimezone(UTC).date().isoformat()


def classify_pr_type(
    label_names: Iterable[str],
    settings: Settings,
) -> PRType:
    """Precedence: bug fix > docs > feature > unclassified."""
    lower = {n.lower() for n in label_names}
    if lower & _parse_sdlc_label_csv(settings.sdlc_bug_labels):
        return "bug_fix"
    if lower & _parse_sdlc_label_csv(settings.sdlc_docs_labels):
        return "docs"
    if lower & _parse_sdlc_label_csv(settings.sdlc_feature_labels):
        return "feature"
    return "unclassified"


def size_bucket_from_lines(changed_lines: int | None) -> SizeBucket:
    if changed_lines is None or changed_lines < 0:
        return "unknown"
    if changed_lines <= 10:
        return "tiny"
    if changed_lines <= 100:
        return "small"
    if changed_lines <= 500:
        return "medium"
    return "large"


def median_seconds(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def median_seconds_by_group(
    items: list[tuple[PRType | str, SizeBucket, float]],
    group_key: Callable[[tuple[PRType | str, SizeBucket, float]], str],
) -> dict[str, float | None]:
    buckets: dict[str, list[float]] = {}
    for row in items:
        key = group_key(row)
        buckets.setdefault(key, []).append(row[2])
    return {k: median_seconds(v) for k, v in buckets.items()}


def is_bot_user(login: str | None, user_type: str | None) -> bool:
    if user_type == "Bot":
        return True
    if not login:
        return False
    if login.endswith("[bot]"):
        return True
    return login.endswith("-bot")


def is_pr_author_bot(author: dict[str, Any] | None) -> bool:
    """True if the PR author is a bot (Dependabot, Mergify, GitHub Actions, etc.)."""
    if not author:
        return False
    login = (author.get("login") or "").strip()
    typename = author.get("__typename") or ""
    rest_type = author.get("type") or ""
    if typename == "Bot" or rest_type == "Bot":
        return True
    if not login:
        return False
    gh_type = rest_type or ("Bot" if typename == "Bot" else "User")
    if is_bot_user(login, gh_type):
        return True
    low = login.lower()
    for prefix in (
        "dependabot",
        "mergify",
        "renovate",
        "greenkeeper",
        "snyk-",
        "pyup-",
        "imgbot",
        "codecov",
    ):
        if low.startswith(prefix):
            return True
    return False


def filter_out_bot_pr_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop PRs authored by bots from GraphQL search results."""
    out: list[dict[str, Any]] = []
    for n in nodes:
        if not n or n.get("number") is None:
            continue
        if is_pr_author_bot(n.get("author")):
            continue
        out.append(n)
    return out


def first_human_review_submitted_at(
    reviews: Sequence[Mapping[str, Any]],
) -> datetime | None:
    """First review by submission time among non-bot authors."""
    candidates: list[datetime] = []
    for r in reviews:
        user = r.get("user") or {}
        login = user.get("login")
        utype = user.get("type")
        if is_bot_user(login, utype):
            continue
        raw = r.get("submitted_at")
        if not raw:
            continue
        try:
            # GitHub returns Z suffix
            candidates.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
        except ValueError:
            continue
    if not candidates:
        return None
    return min(candidates)


def parse_github_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def semver_tuple(title: str) -> tuple[int, int, int]:
    """Parse `vX.Y.Z` title into a tuple for ordering. Caller must validate format."""
    parts = title[1:].split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def _best_closed_on_line(
    closed_milestones: list[dict[str, Any]],
    line: tuple[int, int],
    version_match: re.Pattern[str],
) -> str | None:
    """Latest closed milestone on the given (major, minor) line (highest patch)."""
    best: tuple[str, tuple[int, int, int]] | None = None
    for m in closed_milestones:
        title = m.get("title") or ""
        if not version_match.match(title):
            continue
        t = semver_tuple(title)
        if (t[0], t[1]) != line:
            continue
        if best is None or t > best[1]:
            best = (title, t)
    return best[0] if best else None


def _lowest_open_on_line(
    open_milestones: list[dict[str, Any]],
    line: tuple[int, int],
    version_match: re.Pattern[str],
) -> str | None:
    """Lowest open semver on the given (major, minor) line."""
    titles: list[str] = []
    for m in open_milestones:
        title = m.get("title") or ""
        if not version_match.match(title):
            continue
        t = semver_tuple(title)
        if (t[0], t[1]) == line:
            titles.append(title)
    if not titles:
        return None
    return min(titles, key=semver_tuple)


def select_escaped_defect_milestones(
    open_milestones: list[dict[str, Any]],
    closed_milestones: list[dict[str, Any]],
    *,
    version_match: re.Pattern[str],
) -> list[tuple[str, bool]]:
    """Milestones for escaped defect rate: next open line + two previous minor lines.

    The **first open** milestone is the globally lowest open ``vX.Y.Z``. Included rows:

    * The two **previous** release lines ``(M, m-2)`` and ``(M, m-1)`` when they exist
      (e.g. ``v0.5.x`` and ``v0.6.x`` when the next line is ``v0.7.x``), using the
      **latest closed** milestone per line (highest patch).
    * The **current** line ``(M, m)``: the lowest open milestone on that line
      (pre-release); ``is_next_open`` is True for this row only.

    Rows are returned sorted by **semantic version** (ascending). Lines with no matching
    closed milestone are omitted (except the open line, which requires an open milestone).
    """
    open_semver_titles = [
        m["title"] for m in open_milestones if version_match.match(m.get("title") or "")
    ]
    if not open_semver_titles:
        return []

    next_open = min(open_semver_titles, key=semver_tuple)
    major_v, minor_v, _patch_v = semver_tuple(next_open)

    lines_in_order: list[tuple[int, int]] = []
    if minor_v >= 2:
        lines_in_order.append((major_v, minor_v - 2))
    if minor_v >= 1:
        lines_in_order.append((major_v, minor_v - 1))
    lines_in_order.append((major_v, minor_v))

    out: list[tuple[str, bool]] = []
    for line in lines_in_order:
        if line == (major_v, minor_v):
            title = _lowest_open_on_line(open_milestones, line, version_match)
            if title is None:
                continue
            out.append((title, True))
        else:
            title = _best_closed_on_line(closed_milestones, line, version_match)
            if title is not None:
                out.append((title, False))

    out.sort(key=lambda row: semver_tuple(row[0]))
    return out


def build_semver_milestone_previous_map(
    open_milestones: list[dict[str, Any]],
    closed_milestones: list[dict[str, Any]],
    *,
    version_match: re.Pattern[str],
) -> dict[str, str]:
    """Map each semver milestone title to the immediately prior semver milestone.

    Ordering is global semver order across open and closed milestones. The
    earliest milestone has no predecessor and is omitted from the map.
    """
    titles: set[str] = set()
    for m in open_milestones + closed_milestones:
        t = m.get("title") or ""
        if version_match.match(t):
            titles.add(t)
    ordered = sorted(titles, key=semver_tuple)
    return {ordered[i]: ordered[i - 1] for i in range(1, len(ordered))}


def escape_labeled_issues_query(github_repo: str, escape_label: str) -> str:
    """GitHub issue search query for issues carrying the escape label."""
    lab = escape_label.strip().lower()
    if not lab:
        lab = "escape"
    label_tok = f'label:"{lab}"' if any(c in lab for c in " /") else f"label:{lab}"
    return f"{repo_search_fragment(github_repo)} is:issue {label_tok}"


def rest_search_issue_items_paginated(
    get_fn: Callable[[str], dict[str, Any]],
    q: str,
    *,
    per_page: int = 100,
) -> list[dict[str, Any]]:
    """Walk ``/search/issues`` pages (GitHub caps total results at 1000)."""
    items: list[dict[str, Any]] = []
    page = 1
    while True:
        path = f"/search/issues?q={quote_plus(q)}&per_page={per_page}&page={page}"
        data = get_fn(path)
        batch = data.get("items") or []
        items.extend(batch)
        if len(batch) < per_page:
            break
        if len(items) >= 1000:
            break
        page += 1
    return items


def count_escape_issues_by_prior_milestone(
    escape_items: Iterable[dict[str, Any]],
    issue_milestone_to_prior: dict[str, str],
    *,
    version_match: re.Pattern[str],
) -> dict[str, int]:
    """Attribute each escape issue to the milestone *before* its own milestone."""
    counts: dict[str, int] = {}
    for item in escape_items:
        ms = item.get("milestone")
        if not isinstance(ms, dict):
            continue
        mt = ms.get("title") or ""
        if not version_match.match(str(mt)):
            continue
        prior = issue_milestone_to_prior.get(str(mt))
        if prior is None:
            continue
        counts[prior] = counts.get(prior, 0) + 1
    return counts


def graphql_search_pull_requests(
    post_graphql: Callable[[dict[str, Any]], dict[str, Any]],
    search_query: str,
    *,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    """Paginate GitHub GraphQL search (PullRequest nodes)."""
    nodes: list[dict[str, Any]] = []
    cursor: str | None = None
    gql = """
    query($q: String!, $first: Int!, $after: String) {
      search(query: $q, type: ISSUE, first: $first, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          ... on PullRequest {
            number
            createdAt
            mergedAt
            additions
            deletions
            labels(first: 30) { nodes { name } }
            milestone { title }
            author {
              __typename
              ... on User { login }
              ... on Bot { login }
              ... on Organization { login }
            }
          }
        }
      }
    }
    """
    while True:
        payload = {
            "query": gql,
            "variables": {
                "q": search_query,
                "first": page_size,
                "after": cursor,
            },
        }
        data = post_graphql(payload)
        errors = data.get("errors")
        if errors:
            logger.error("GraphQL errors: %s", errors)
            raise RuntimeError(f"GitHub GraphQL error: {errors!r}")
        search = data.get("data", {}).get("search") or {}
        batch = search.get("nodes") or []
        nodes.extend(filter_out_bot_pr_nodes(batch))
        page = search.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        if not cursor:
            break
    return nodes


def repo_search_fragment(github_repo: str) -> str:
    return f"repo:{github_repo}"


def merged_prs_query(github_repo: str, merged_since: datetime) -> str:
    return (
        f"{repo_search_fragment(github_repo)} is:pr is:merged "
        f"merged:>={date_str(merged_since)}"
    )


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


def rest_search_total_count(
    get_fn: Callable[[str], dict[str, Any]],
    q: str,
) -> int:
    """GET /search/issues total_count."""
    path = f"/search/issues?q={quote_plus(q)}"
    data = get_fn(path)
    return int(data.get("total_count", 0))


def pr_row_from_graphql_node(
    node: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    labels = [ln["name"] for ln in (node.get("labels") or {}).get("nodes") or []]
    pr_type = classify_pr_type(labels, settings)
    add = node.get("additions")
    de = node.get("deletions")
    try:
        changed = (add or 0) + (de or 0)
    except TypeError:
        changed = 0
    bucket = size_bucket_from_lines(changed)
    created = parse_github_ts(node.get("createdAt"))
    merged = parse_github_ts(node.get("mergedAt"))
    return {
        "number": node["number"],
        "pr_type": pr_type,
        "size_bucket": bucket,
        "changed_lines": changed,
        "created_at": created,
        "merged_at": merged,
        "milestone_title": (node.get("milestone") or {}).get("title"),
    }


def aggregate_throughput(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, int] = {
        "feature": 0,
        "bug_fix": 0,
        "docs": 0,
        "unclassified": 0,
    }
    by_size: dict[str, int] = {
        "tiny": 0,
        "small": 0,
        "medium": 0,
        "large": 0,
        "unknown": 0,
    }
    for r in rows:
        pt = str(r["pr_type"])
        by_type[pt] = by_type.get(pt, 0) + 1
        sb = str(r["size_bucket"])
        by_size[sb] = by_size.get(sb, 0) + 1
    return {"total": len(rows), "by_pr_type": by_type, "by_pr_size": by_size}


def build_median_cycle_payload(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    triples: list[tuple[PRType | str, SizeBucket, float]] = []
    for r in rows:
        c, m = r.get("created_at"), r.get("merged_at")
        if not c or not m:
            continue
        dt = max(0.0, (m - c).total_seconds())
        triples.append((str(r["pr_type"]), str(r["size_bucket"]), dt))  # type: ignore[arg-type]

    overall = median_seconds([t[2] for t in triples])
    by_type = median_seconds_by_group(triples, lambda t: str(t[0]))
    by_size = median_seconds_by_group(triples, lambda t: str(t[1]))
    return {
        "median_seconds": overall,
        "by_pr_type": by_type,
        "by_pr_size": by_size,
        "pr_count": len(triples),
    }


def build_first_review_payload(
    rows_with_review: Sequence[tuple[Mapping[str, Any], float]],
    eligible_count: int,
) -> dict[str, Any]:
    triples: list[tuple[str, str, float]] = []
    for r, secs in rows_with_review:
        triples.append((str(r["pr_type"]), str(r["size_bucket"]), secs))

    overall = median_seconds([t[2] for t in triples])
    by_type = median_seconds_by_group(triples, lambda t: t[0])
    by_size = median_seconds_by_group(triples, lambda t: t[1])
    return {
        "median_seconds": overall,
        "by_pr_type": by_type,
        "by_pr_size": by_size,
        "included_pr_count": len(triples),
        "eligible_pr_count": eligible_count,
    }
