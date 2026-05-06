"""SDLC KPI REST endpoints (GitHub-backed)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from github_pm.api import connection, Connector
from github_pm.context import context
from github_pm.sdlc_models import (
    BugBacklogResponse,
    DeliveryResponse,
    EscapedDefectResponse,
)
from github_pm import sdlc_service

sdlc_router = APIRouter(prefix="/sdlc", tags=["sdlc"])


@sdlc_router.get("/delivery", response_model=DeliveryResponse)
async def get_sdlc_delivery(
    gitctx: Annotated[Connector, Depends(connection)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
):
    """
    Delivery metrics: merged PR throughput, median cycle time, median time to first human review.
    PRs authored by bots (Dependabot, Mergify, etc.) are excluded from all delivery stats.
    Reviews exclude GitHub bots. Time-to-first-review uses human-authored PRs opened in the window
    with at least one human review (see eligible vs included counts).
    """
    return sdlc_service.compute_sdlc_delivery(gitctx, context, days=days)


@sdlc_router.get("/escaped-defect-rate", response_model=EscapedDefectResponse)
async def get_escaped_defect_rate(
    gitctx: Annotated[Connector, Depends(connection)],
):
    """
    Escaped defect rate for the **lowest open** semver milestone (next release line) plus
    the **two previous** release lines on the same major (e.g. ``v0.5.x`` and ``v0.6.x``
    when the next line is ``v0.7.x``), using the latest closed milestone per previous line.

    Escapes are **issues** with the ``sdlc_escape_label`` (default ``escape``) and a semver
    milestone; each counts toward the **previous** milestone in global semver order.
    Rate is ``escape_issues / (feature_prs + bug_fix_prs + docs_prs)`` for merged PRs in each milestone.
    Bot-authored PRs are excluded from denominators.
    """
    return sdlc_service.compute_escaped_defect_rate(gitctx, context)


@sdlc_router.get("/bug-backlog-delta", response_model=BugBacklogResponse)
async def get_bug_backlog_delta(
    gitctx: Annotated[Connector, Depends(connection)],
    days: Annotated[int, Query(ge=1, le=90)] = 7,
):
    """Net bug backlog change: bug issues created minus bug issues closed in the window."""
    return sdlc_service.compute_bug_backlog_delta(gitctx, context, days=days)
