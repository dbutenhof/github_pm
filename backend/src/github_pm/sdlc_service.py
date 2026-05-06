"""Shared SDLC KPI computation (used by FastAPI routes).

The standalone ``sdlc-report`` script (``scripts/sdlc_report.py``) mirrors this
logic without importing ``github_pm``; keep behavior aligned when changing
metrics.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from github_pm import sdlc_metrics as sm
from github_pm.api import Connector, VERSION_MATCH
from github_pm.context import Settings
from github_pm.logger import logger
from github_pm.sdlc_models import (
    BugBacklogResponse,
    BugBacklogSeriesResponse,
    CycleTimePayload,
    DeliveryResponse,
    DeliverySeriesResponse,
    EscapedDefectResponse,
    EscapedDefectRow,
    EscapedDefectSeriesResponse,
    FirstReviewPayload,
    ThroughputBreakdown,
)


def _post_graphql(gitctx: Connector):
    return lambda payload: gitctx.post("/graphql", payload)


def _github_repo(gitctx: Connector) -> str:
    return f"{gitctx.owner}/{gitctx.repo}"


def _filter_merged_in_slice(
    rows: list[dict[str, Any]],
    window_start: datetime,
    window_end: datetime,
) -> list[dict[str, Any]]:
    """Half-open on the left: merged in (window_start, window_end]."""
    out: list[dict[str, Any]] = []
    for r in rows:
        m = r.get("merged_at")
        if not m:
            continue
        if window_start < m <= window_end:
            out.append(r)
    return out


def _filter_created_in_slice(
    rows: list[dict[str, Any]],
    window_start: datetime,
    window_end: datetime,
) -> list[dict[str, Any]]:
    """Half-open on the left: created in (window_start, window_end]."""
    out: list[dict[str, Any]] = []
    for r in rows:
        c = r.get("created_at")
        if not c:
            continue
        if window_start < c <= window_end:
            out.append(r)
    return out


def compute_sdlc_delivery(
    gitctx: Connector,
    settings: Settings,
    *,
    days: int = 7,
    now: datetime | None = None,
) -> DeliveryResponse:
    """Delivery metrics (throughput, cycle time, time to first human review).

    Window is ``(now - days, now]`` (UTC): merged and created timestamps strictly after
    ``now - days`` and on or before ``now``.
    """
    repo = _github_repo(gitctx)
    window_end = now if now is not None else sm.utc_now()
    window_start = window_end - timedelta(days=days)

    merged_q = sm.merged_prs_query(repo, window_start)
    merged_nodes = sm.graphql_search_pull_requests(_post_graphql(gitctx), merged_q)
    merged_rows = [sm.pr_row_from_graphql_node(n, settings) for n in merged_nodes]
    merged_rows = _filter_merged_in_slice(merged_rows, window_start, window_end)

    throughput = sm.aggregate_throughput(merged_rows)
    cycle = sm.build_median_cycle_payload(merged_rows)

    opened_q = sm.opened_prs_query(repo, window_start)
    opened_nodes = sm.graphql_search_pull_requests(_post_graphql(gitctx), opened_q)
    opened_rows = [sm.pr_row_from_graphql_node(n, settings) for n in opened_nodes]
    opened_rows = _filter_created_in_slice(opened_rows, window_start, window_end)

    rows_with_review: list[tuple[dict[str, Any], float]] = []
    for r in opened_rows:
        num = r["number"]
        try:
            raw = gitctx.get(
                f"/repos/{gitctx.owner}/{gitctx.repo}/pulls/{num}/reviews",
                headers={"Accept": "application/vnd.github+json"},
            )
        except Exception as e:
            logger.warning("Failed to fetch reviews for PR %s: %s", num, e)
            continue
        if not isinstance(raw, list):
            logger.warning(
                "Reviews for PR %s: expected JSON array, got %s", num, type(raw)
            )
            continue
        rev_list: list[dict[str, Any]] = raw
        first_at = sm.first_human_review_submitted_at(rev_list)
        created = r.get("created_at")
        if first_at and created:
            secs = max(0.0, (first_at - created).total_seconds())
            rows_with_review.append((r, secs))

    review_payload = sm.build_first_review_payload(
        rows_with_review, eligible_count=len(opened_rows)
    )

    return DeliveryResponse(
        window_days=days,
        window_start=window_start,
        window_end=window_end,
        as_of=window_end,
        merged_pr_throughput=ThroughputBreakdown(**throughput),
        median_pr_cycle_time=CycleTimePayload(**cycle),
        median_time_to_first_review=FirstReviewPayload(**review_payload),
    )


def compute_sdlc_delivery_series(
    gitctx: Connector,
    settings: Settings,
    *,
    weeks: int,
    week_days: int = 7,
) -> DeliverySeriesResponse:
    """One delivery slice per week, oldest slice first."""
    now = sm.utc_now()
    slices: list[DeliveryResponse] = []
    for i in range(weeks):
        window_end = now - timedelta(days=i * week_days)
        slices.append(
            compute_sdlc_delivery(gitctx, settings, days=week_days, now=window_end)
        )
    slices.reverse()
    return DeliverySeriesResponse(weeks=weeks, week_days=week_days, slices=slices)


def compute_escaped_defect_rate(
    gitctx: Connector,
    settings: Settings,
) -> EscapedDefectResponse:
    now = sm.utc_now()
    repo = _github_repo(gitctx)
    open_milestones = gitctx.get_paged(
        f"/repos/{repo}/milestones?state=open",
        headers={"Accept": "application/vnd.github+json"},
    )
    closed_milestones = gitctx.get_paged(
        f"/repos/{repo}/milestones?state=closed",
        headers={"Accept": "application/vnd.github+json"},
    )
    targets = sm.select_escaped_defect_milestones(
        open_milestones,
        closed_milestones,
        version_match=VERSION_MATCH,
    )
    issue_milestone_to_prior = sm.build_semver_milestone_previous_map(
        open_milestones,
        closed_milestones,
        version_match=VERSION_MATCH,
    )
    escape_q = sm.escape_labeled_issues_query(repo, settings.sdlc_escape_label)
    escape_items = sm.rest_search_issue_items_paginated(
        lambda path: gitctx.get(path),
        escape_q,
    )
    escapes_by_release = sm.count_escape_issues_by_prior_milestone(
        escape_items,
        issue_milestone_to_prior,
        version_match=VERSION_MATCH,
    )
    releases: list[EscapedDefectRow] = []
    post = _post_graphql(gitctx)

    for title, is_next_open in targets:
        q = sm.milestone_merged_prs_query(repo, title)
        nodes = sm.graphql_search_pull_requests(post, q)
        rows = [sm.pr_row_from_graphql_node(n, settings) for n in nodes]
        feat = sum(1 for r in rows if r["pr_type"] == "feature")
        bugs = sum(1 for r in rows if r["pr_type"] == "bug_fix")
        docs = sum(1 for r in rows if r["pr_type"] == "docs")
        denom = feat + bugs + docs
        esc = int(escapes_by_release.get(title, 0))
        rate = (esc / denom) if denom else None
        releases.append(
            EscapedDefectRow(
                release=title,
                feature_prs=feat,
                bug_fix_prs=bugs,
                docs_prs=docs,
                escape_issues=esc,
                rate=rate,
                is_next_open=is_next_open,
            )
        )

    return EscapedDefectResponse(as_of=now, releases=releases)


def compute_escaped_defect_rate_series(
    gitctx: Connector,
    settings: Settings,
    *,
    weeks: int,
    week_days: int = 7,
) -> EscapedDefectSeriesResponse:
    """Incremental escaped defect stats per week (oldest slice first).

    Milestone selection uses **current** open/closed milestones. Denominators count
    non-bot PRs merged into each target milestone with ``merged_at`` in the slice;
    numerators count escape-labeled issues **created** in the slice whose milestone
    maps to that row via ``issue_milestone_to_prior`` (same attribution as the
    cumulative endpoint).
    """
    now = sm.utc_now()
    repo = _github_repo(gitctx)
    open_milestones = gitctx.get_paged(
        f"/repos/{repo}/milestones?state=open",
        headers={"Accept": "application/vnd.github+json"},
    )
    closed_milestones = gitctx.get_paged(
        f"/repos/{repo}/milestones?state=closed",
        headers={"Accept": "application/vnd.github+json"},
    )
    targets = sm.select_escaped_defect_milestones(
        open_milestones,
        closed_milestones,
        version_match=VERSION_MATCH,
    )
    issue_milestone_to_prior = sm.build_semver_milestone_previous_map(
        open_milestones,
        closed_milestones,
        version_match=VERSION_MATCH,
    )
    escape_q = sm.escape_labeled_issues_query(repo, settings.sdlc_escape_label)
    escape_items = sm.rest_search_issue_items_paginated(
        lambda path: gitctx.get(path),
        escape_q,
    )
    post = _post_graphql(gitctx)
    rows_by_title: dict[str, list[dict[str, Any]]] = {}
    for title, _is_next_open in targets:
        q = sm.milestone_merged_prs_query(repo, title)
        nodes = sm.graphql_search_pull_requests(post, q)
        rows_by_title[title] = [sm.pr_row_from_graphql_node(n, settings) for n in nodes]

    slices: list[EscapedDefectResponse] = []
    for i in range(weeks):
        window_end = now - timedelta(days=i * week_days)
        window_start = window_end - timedelta(days=week_days)
        releases: list[EscapedDefectRow] = []
        for title, is_next_open in targets:
            rows = rows_by_title[title]
            in_win = [
                r
                for r in rows
                if r.get("merged_at") and window_start < r["merged_at"] <= window_end
            ]
            feat = sum(1 for r in in_win if r["pr_type"] == "feature")
            bugs = sum(1 for r in in_win if r["pr_type"] == "bug_fix")
            docs = sum(1 for r in in_win if r["pr_type"] == "docs")
            denom = feat + bugs + docs
            esc = 0
            for item in escape_items:
                ts = sm.parse_github_ts(item.get("created_at"))
                if ts is None or not (window_start < ts <= window_end):
                    continue
                ms = item.get("milestone")
                if not isinstance(ms, dict):
                    continue
                mt = str(ms.get("title") or "")
                if not VERSION_MATCH.match(mt):
                    continue
                prior = issue_milestone_to_prior.get(mt)
                if prior != title:
                    continue
                esc += 1
            rate = (esc / denom) if denom else None
            releases.append(
                EscapedDefectRow(
                    release=title,
                    feature_prs=feat,
                    bug_fix_prs=bugs,
                    docs_prs=docs,
                    escape_issues=esc,
                    rate=rate,
                    is_next_open=is_next_open,
                )
            )
        slices.append(
            EscapedDefectResponse(
                window_start=window_start,
                window_end=window_end,
                as_of=window_end,
                releases=releases,
            )
        )
    slices.reverse()
    return EscapedDefectSeriesResponse(weeks=weeks, week_days=week_days, slices=slices)


def _count_bug_issues_in_slice(
    gitctx: Connector,
    repo: str,
    labels: str,
    window_start: datetime,
    window_end: datetime,
    *,
    opened: bool,
) -> int:
    """Count bug issues opened or closed in ``(window_start, window_end]`` (UTC)."""
    q = (
        sm.bug_issues_created_query_between(repo, labels, window_start, window_end)
        if opened
        else sm.bug_issues_closed_query_between(repo, labels, window_start, window_end)
    )
    items = sm.rest_search_issue_items_paginated(
        lambda path: gitctx.get(path),
        q,
    )
    key = "created_at" if opened else "closed_at"
    n = 0
    for item in items:
        raw = item.get(key)
        ts = sm.parse_github_ts(raw) if raw else None
        if ts is not None and window_start < ts <= window_end:
            n += 1
    return n


def compute_bug_backlog_delta(
    gitctx: Connector,
    settings: Settings,
    *,
    days: int = 7,
    now: datetime | None = None,
) -> BugBacklogResponse:
    window_end = now if now is not None else sm.utc_now()
    window_start = window_end - timedelta(days=days)
    repo = _github_repo(gitctx)
    labels = settings.sdlc_bug_labels

    opened = _count_bug_issues_in_slice(
        gitctx, repo, labels, window_start, window_end, opened=True
    )
    closed = _count_bug_issues_in_slice(
        gitctx, repo, labels, window_start, window_end, opened=False
    )

    return BugBacklogResponse(
        window_days=days,
        window_start=window_start,
        window_end=window_end,
        as_of=window_end,
        bugs_opened=opened,
        bugs_closed=closed,
        net=opened - closed,
    )


def compute_bug_backlog_delta_series(
    gitctx: Connector,
    settings: Settings,
    *,
    weeks: int,
    week_days: int = 7,
) -> BugBacklogSeriesResponse:
    now = sm.utc_now()
    slices: list[BugBacklogResponse] = []
    for i in range(weeks):
        window_end = now - timedelta(days=i * week_days)
        slices.append(
            compute_bug_backlog_delta(gitctx, settings, days=week_days, now=window_end)
        )
    slices.reverse()
    return BugBacklogSeriesResponse(weeks=weeks, week_days=week_days, slices=slices)
