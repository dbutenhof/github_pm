"""REST API for the weekly project status report."""

from __future__ import annotations

from datetime import date, datetime, UTC
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from github_pm.api import connection, Connector
from github_pm.status_report_models import ProjectStatusReportResponse
from github_pm.status_report_service import build_project_status_report

status_report_router = APIRouter(tags=["project-status"])


def _default_end_date() -> date:
    return datetime.now(UTC).date()


@status_report_router.get("/project-status", response_model=ProjectStatusReportResponse)
async def get_project_status_report(
    gitctx: Annotated[Connector, Depends(connection)],
    end_date: Annotated[
        date | None,
        Query(
            description="Last day of the 7-day window (UTC calendar date). Defaults to today in UTC.",
        ),
    ] = None,
):
    """
    Status for seven **calendar** days inclusive: ``end_date - 6 days`` through ``end_date``.

    Sections: merged pull requests (by merge date), pull requests opened, issues opened (PRs excluded).
    """
    resolved_end = end_date if end_date is not None else _default_end_date()
    return build_project_status_report(gitctx, end_date=resolved_end)
