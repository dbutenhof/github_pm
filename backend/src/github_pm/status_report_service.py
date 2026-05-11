"""Project status report via GraphQL ``search``

Generated-by: Cursor
"""

from __future__ import annotations

from datetime import date, UTC
from typing import Any

from github_pm import sdlc_metrics as sm
from github_pm.api import Connector
from github_pm.status_report_models import ProjectStatusReportResponse, StatusReportItem


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


def _updated_strictly_before_start_date(node: dict[str, Any], start_d: date) -> bool:
    """True if ``updatedAt`` exists and its UTC calendar date is before ``start_d``."""
    u = sm.parse_github_ts(node.get("updatedAt"))
    if not u:
        return False
    return u.astimezone(UTC).date() < start_d


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
    backlog_items = [_item_from_gql_node(n) for n in backlog_filtered]

    return ProjectStatusReportResponse(
        start_date=start_date,
        end_date=end_date,
        merged_pull_requests=merged_items,
        opened_pull_requests=[_item_from_gql_node(n) for n in opened_pr_filtered],
        opened_issues=[_item_from_gql_node(n) for n in opened_issue_filtered],
        pr_backlog=backlog_items,
    )
