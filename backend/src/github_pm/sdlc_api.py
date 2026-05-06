"""SDLC KPI REST endpoints (GitHub-backed)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from github_pm import sdlc_service
from github_pm.api import connection, Connector
from github_pm.context import context
from github_pm.sdlc_models import (
    BugBacklogSeriesResponse,
    DeliverySeriesResponse,
    EscapedDefectSeriesResponse,
)

sdlc_router = APIRouter(prefix="/sdlc", tags=["sdlc"])


@sdlc_router.get("/delivery", response_model=DeliverySeriesResponse)
async def get_sdlc_delivery(
    gitctx: Annotated[Connector, Depends(connection)],
    weeks: Annotated[int, Query(ge=1, le=52)] = 4,
    week_days: Annotated[int, Query(ge=1, le=90)] = 7,
):
    """
    Delivery metrics: merged PR throughput, median cycle time, median time to first human review,
    repeated for each of the last ``weeks`` windows of ``week_days`` days (oldest slice first).

    Each slice window is ``(slice_end - week_days, slice_end]`` in UTC. PRs authored by bots
    (Dependabot, Mergify, etc.) are excluded from all delivery stats. Reviews exclude GitHub bots.
    """
    return sdlc_service.compute_sdlc_delivery_series(
        gitctx, context, weeks=weeks, week_days=week_days
    )


@sdlc_router.get("/escaped-defect-rate", response_model=EscapedDefectSeriesResponse)
async def get_escaped_defect_rate(
    gitctx: Annotated[Connector, Depends(connection)],
    weeks: Annotated[int, Query(ge=1, le=52)] = 4,
    week_days: Annotated[int, Query(ge=1, le=90)] = 7,
):
    """
    Escaped defect metrics per week (oldest slice first). Milestone rows match the cumulative
    endpoint (next open line plus two previous minors), but counts are **incremental** within
    each ``week_days`` window: PRs merged into the milestone and escape issues **created** in
    that window (same prior-milestone attribution). Bot-authored PRs are excluded from denominators.
    """
    return sdlc_service.compute_escaped_defect_rate_series(
        gitctx, context, weeks=weeks, week_days=week_days
    )


@sdlc_router.get("/bug-backlog-delta", response_model=BugBacklogSeriesResponse)
async def get_bug_backlog_delta(
    gitctx: Annotated[Connector, Depends(connection)],
    weeks: Annotated[int, Query(ge=1, le=52)] = 4,
    week_days: Annotated[int, Query(ge=1, le=90)] = 7,
):
    """Bug issues opened, closed, and net per week (``weeks`` slices of ``week_days``, oldest first)."""
    return sdlc_service.compute_bug_backlog_delta_series(
        gitctx, context, weeks=weeks, week_days=week_days
    )
