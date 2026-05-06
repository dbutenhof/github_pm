"""Shared SDLC KPI computation (used by FastAPI routes).

The standalone ``sdlc-report`` script (``scripts/sdlc_report.py``) mirrors this
logic without importing ``github_pm``; keep behavior aligned when changing
metrics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from github_pm.api import VERSION_MATCH, Connector
from github_pm.context import Settings
from github_pm.logger import logger
from github_pm import sdlc_metrics as sm
from github_pm.sdlc_models import (
    BugBacklogResponse,
    CycleTimePayload,
    DeliveryResponse,
    EscapedDefectResponse,
    EscapedDefectRow,
    FirstReviewPayload,
    ThroughputBreakdown,
)


def _post_graphql(gitctx: Connector):
    return lambda payload: gitctx.post("/graphql", payload)


def _github_repo(gitctx: Connector) -> str:
    return f"{gitctx.owner}/{gitctx.repo}"


def _filter_merged_in_window(
    rows: list[dict[str, Any]],
    window_start: datetime,
    now: datetime,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        m = r.get("merged_at")
        if not m:
            continue
        if m >= window_start and m <= now:
            out.append(r)
    return out


def _filter_created_in_window(
    rows: list[dict[str, Any]],
    window_start: datetime,
    now: datetime,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        c = r.get("created_at")
        if not c:
            continue
        if c >= window_start and c <= now:
            out.append(r)
    return out


def compute_sdlc_delivery(
    gitctx: Connector,
    settings: Settings,
    *,
    days: int = 7,
) -> DeliveryResponse:
    """Delivery metrics (throughput, cycle time, time to first human review)."""
    repo = _github_repo(gitctx)
    now = sm.utc_now()
    window_start = sm.window_start(days, now)

    merged_q = sm.merged_prs_query(repo, window_start)
    merged_nodes = sm.graphql_search_pull_requests(_post_graphql(gitctx), merged_q)
    merged_rows = [sm.pr_row_from_graphql_node(n, settings) for n in merged_nodes]
    merged_rows = _filter_merged_in_window(merged_rows, window_start, now)

    throughput = sm.aggregate_throughput(merged_rows)
    cycle = sm.build_median_cycle_payload(merged_rows)

    opened_q = sm.opened_prs_query(repo, window_start)
    opened_nodes = sm.graphql_search_pull_requests(_post_graphql(gitctx), opened_q)
    opened_rows = [sm.pr_row_from_graphql_node(n, settings) for n in opened_nodes]
    opened_rows = _filter_created_in_window(opened_rows, window_start, now)

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
            logger.warning("Reviews for PR %s: expected JSON array, got %s", num, type(raw))
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
        as_of=now,
        merged_pr_throughput=ThroughputBreakdown(**throughput),
        median_pr_cycle_time=CycleTimePayload(**cycle),
        median_time_to_first_review=FirstReviewPayload(**review_payload),
    )


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


def compute_bug_backlog_delta(
    gitctx: Connector,
    settings: Settings,
    *,
    days: int = 7,
) -> BugBacklogResponse:
    now = sm.utc_now()
    window_start = sm.window_start(days, now)
    repo = _github_repo(gitctx)
    labels = settings.sdlc_bug_labels

    q_opened = sm.bug_issues_created_query(repo, labels, window_start)
    q_closed = sm.bug_issues_closed_query(repo, labels, window_start)

    opened = sm.rest_search_total_count(lambda path: gitctx.get(path), q_opened)
    closed = sm.rest_search_total_count(lambda path: gitctx.get(path), q_closed)

    return BugBacklogResponse(
        window_days=days,
        as_of=now,
        bugs_opened=opened,
        bugs_closed=closed,
        net=opened - closed,
    )
