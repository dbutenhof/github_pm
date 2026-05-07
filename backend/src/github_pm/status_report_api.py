"""REST API for the project status report.

Generated-by: Cursor
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from github_pm.api import connection, Connector
from github_pm.status_report_models import ProjectStatusReportResponse
from github_pm.status_report_service import build_project_status_report

status_report_router = APIRouter(tags=["project-status"])

_MAX_RANGE_DAYS = 365


def _default_end_date() -> date:
    return datetime.now(UTC).date()


@status_report_router.get("/project-status", response_model=ProjectStatusReportResponse)
async def get_project_status_report(
    gitctx: Annotated[Connector, Depends(connection)],
    start_date: Annotated[
        date | None,
        Query(
            description="First day of the window (UTC calendar date). Defaults to 7 days before end_date.",
        ),
    ] = None,
    end_date: Annotated[
        date | None,
        Query(
            description="Last day of the window (UTC calendar date). Defaults to today in UTC.",
        ),
    ] = None,
):
    """
    Status for the inclusive calendar range ``start_date`` … ``end_date`` (UTC).

    Defaults: ``end_date`` = today (UTC), ``start_date`` = ``end_date`` minus 7 calendar days.

    Sections: merged pull requests (by merge date), pull requests opened, issues opened (PRs excluded).
    """
    resolved_end = end_date if end_date is not None else _default_end_date()
    resolved_start = (
        start_date if start_date is not None else resolved_end - timedelta(days=7)
    )
    if resolved_start > resolved_end:
        raise HTTPException(
            status_code=422,
            detail="start_date must be on or before end_date",
        )
    if (resolved_end - resolved_start).days > _MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=422,
            detail="Date range must not span more than 366 calendar days",
        )
    return build_project_status_report(
        gitctx,
        start_date=resolved_start,
        end_date=resolved_end,
    )
