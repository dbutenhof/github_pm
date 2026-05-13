"""Project status report via GraphQL ``search``

Generated-by: Cursor
"""

from __future__ import annotations

from datetime import date, datetime, UTC
from typing import Any

from github_pm import sdlc_metrics as sm
from github_pm.api import Connector
from github_pm.status_report_models import (
    PrBacklogItem,
    ProjectStatusReportResponse,
    StatusReportItem,
)


def _item_from_gql_node(node: dict[str, Any]) -> StatusReportItem:
    return StatusReportItem(
        number=int(node["number"]),
        title=str(node.get("title") or ""),
        html_url=str(node.get("url") or ""),
    )


def _merged_calendar_in_window(
    node: dict[str, Any], start_d: date, end_d: date
) -> bool:
    m = sm.parse_github_ts(node.get("mergedAt"))
    if not m:
        return False
    md = m.astimezone(UTC).date()
    return start_d <= md <= end_d


def _created_calendar_in_window(
    node: dict[str, Any], start_d: date, end_d: date
) -> bool:
    c = sm.parse_github_ts(node.get("createdAt"))
    if not c:
        return False
    cd = c.astimezone(UTC).date()
    return start_d <= cd <= end_d


def _updated_calendar_in_window(
    node: dict[str, Any], start_d: date, end_d: date
) -> bool:
    u = sm.parse_github_ts(node.get("updatedAt"))
    if not u:
        return False
    ud = u.astimezone(UTC).date()
    return start_d <= ud <= end_d


def _updated_strictly_before_start_date(node: dict[str, Any], start_d: date) -> bool:
    """True if ``updatedAt`` exists and its UTC calendar date is before ``start_d``."""
    u = sm.parse_github_ts(node.get("updatedAt"))
    if not u:
        return False
    return u.astimezone(UTC).date() < start_d


def _calendar_days_since_update_to_end(node: dict[str, Any], end_d: date) -> int:
    """Calendar days from ``updatedAt`` UTC date through ``end_d`` (inclusive span)."""
    u = sm.parse_github_ts(node.get("updatedAt"))
    if not u:
        return 0
    ud = u.astimezone(UTC).date()
    return max(0, (end_d - ud).days)


def _backlog_item_from_gql_node(node: dict[str, Any], end_d: date) -> PrBacklogItem:
    base = _item_from_gql_node(node)
    return PrBacklogItem(
        number=base.number,
        title=base.title,
        html_url=base.html_url,
        days_since_update=_calendar_days_since_update_to_end(node, end_d),
    )


def _max_submitted_review_time(node: dict[str, Any]) -> datetime | None:
    """Latest ``submittedAt`` among non-pending PR reviews, or ``None`` if none."""
    best: datetime | None = None
    for r in (node.get("reviews") or {}).get("nodes") or []:
        if not isinstance(r, dict):
            continue
        if r.get("state") == "PENDING":
            continue
        ts = sm.parse_github_ts(r.get("submittedAt"))
        if ts is None:
            continue
        if best is None or ts > best:
            best = ts
    return best


def _partition_attention_open_prs(
    nodes: list[dict[str, Any]],
) -> tuple[list[StatusReportItem], list[StatusReportItem]]:
    """Split open PR nodes into reviewer vs creator attention lists."""
    reviewer_out: list[StatusReportItem] = []
    creator_out: list[StatusReportItem] = []
    for n in nodes:
        if n.get("state") != "OPEN" or n.get("mergedAt"):
            continue
        updated = sm.parse_github_ts(n.get("updatedAt"))
        if updated is None:
            continue
        last_review = _max_submitted_review_time(n)
        mergeable = str(n.get("mergeable") or "")
        merge_state = str(n.get("mergeStateStatus") or "")
        is_draft = bool(n.get("isDraft"))
        needs_creator_branch = mergeable == "CONFLICTING" or merge_state in (
            "BEHIND",
            "DIRTY",
        )
        if (
            not is_draft
            and mergeable == "MERGEABLE"
            and merge_state not in ("BEHIND", "DIRTY")
            and (last_review is None or updated > last_review)
        ):
            reviewer_out.append(_item_from_gql_node(n))
        if needs_creator_branch or (last_review is not None and last_review > updated):
            creator_out.append(_item_from_gql_node(n))
    reviewer_out.sort(key=lambda x: x.number)
    creator_out.sort(key=lambda x: x.number)
    return reviewer_out, creator_out


def build_project_status_report(
    gitctx: Connector,
    *,
    start_date: date,
    end_date: date,
) -> ProjectStatusReportResponse:
    """Build the report for ``start_date`` through ``end_date`` (inclusive, UTC calendar dates)."""
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    repo = f"{gitctx.owner}/{gitctx.repo}"

    def post_gql(payload: dict[str, Any]) -> dict[str, Any]:
        return gitctx.post("/graphql", payload)

    merged_q = sm.merged_prs_query_between(repo, start_date, end_date)
    merged_nodes = sm.graphql_search_pull_requests(
        post_gql,
        merged_q,
        filter_bot_authors=False,
    )
    merged_in_window = [
        n for n in merged_nodes if _merged_calendar_in_window(n, start_date, end_date)
    ]
    merged_in_window.sort(key=lambda n: int(n["number"]))
    merged_items = [_item_from_gql_node(n) for n in merged_in_window]

    opened_pr_q = sm.opened_prs_between_query(repo, start_date, end_date)
    opened_pr_nodes = sm.graphql_search_timeline_nodes(post_gql, opened_pr_q)
    opened_pr_filtered = [
        n
        for n in opened_pr_nodes
        if n.get("__typename") == "PullRequest"
        and _created_calendar_in_window(n, start_date, end_date)
        and n.get("state") != "CLOSED"
    ]
    opened_pr_filtered.sort(key=lambda n: int(n["number"]))

    opened_issue_q = sm.opened_issues_between_query(repo, start_date, end_date)
    opened_issue_nodes = sm.graphql_search_timeline_nodes(post_gql, opened_issue_q)
    opened_issue_filtered = [
        n
        for n in opened_issue_nodes
        if n.get("__typename") == "Issue"
        and _created_calendar_in_window(n, start_date, end_date)
    ]
    opened_issue_filtered.sort(key=lambda n: int(n["number"]))

    recently_q = sm.open_prs_updated_between_query(repo, start_date, end_date)
    recently_nodes = sm.graphql_search_pull_requests(
        post_gql,
        recently_q,
        filter_bot_authors=False,
    )
    recently_filtered = [
        n
        for n in recently_nodes
        if n.get("state") == "OPEN"
        and not n.get("mergedAt")
        and not n.get("isDraft")
        and _updated_calendar_in_window(n, start_date, end_date)
        and not _created_calendar_in_window(n, start_date, end_date)
    ]
    recently_filtered.sort(key=lambda n: int(n["number"]))
    recently_items = [_item_from_gql_node(n) for n in recently_filtered]

    attention_q = sm.open_pull_requests_for_attention_query(repo)
    attention_nodes = sm.graphql_search_open_pull_requests_attention(
        post_gql,
        attention_q,
        filter_bot_authors=False,
    )
    reviewer_attention, creator_attention = _partition_attention_open_prs(
        attention_nodes
    )

    backlog_q = sm.open_pr_backlog_query(repo, start_date)
    backlog_nodes = sm.graphql_search_pull_requests(
        post_gql,
        backlog_q,
        filter_bot_authors=False,
    )
    backlog_filtered = [
        n
        for n in backlog_nodes
        if n.get("state") == "OPEN"
        and not n.get("mergedAt")
        and not n.get("isDraft")
        and _updated_strictly_before_start_date(n, start_date)
    ]
    backlog_filtered.sort(key=lambda n: int(n["number"]))
    backlog_items = [_backlog_item_from_gql_node(n, end_date) for n in backlog_filtered]

    return ProjectStatusReportResponse(
        start_date=start_date,
        end_date=end_date,
        merged_pull_requests=merged_items,
        opened_pull_requests=[_item_from_gql_node(n) for n in opened_pr_filtered],
        opened_issues=[_item_from_gql_node(n) for n in opened_issue_filtered],
        recently_updated_pull_requests=recently_items,
        reviewer_attention_needed=reviewer_attention,
        creator_attention_needed=creator_attention,
        pr_backlog=backlog_items,
    )
