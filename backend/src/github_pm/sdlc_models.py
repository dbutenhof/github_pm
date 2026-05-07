"""Pydantic models for SDLC KPI API responses.

Generated-by: Cursor
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ThroughputBreakdown(BaseModel):
    total: int
    by_pr_type: dict[str, int]
    by_pr_size: dict[str, int]


class CycleTimePayload(BaseModel):
    median_seconds: float | None
    by_pr_type: dict[str, float | None]
    by_pr_size: dict[str, float | None]
    pr_count: int


class FirstReviewPayload(BaseModel):
    median_seconds: float | None
    by_pr_type: dict[str, float | None]
    by_pr_size: dict[str, float | None]
    included_pr_count: int
    eligible_pr_count: int


class DeliveryResponse(BaseModel):
    window_days: int
    window_start: datetime
    window_end: datetime
    as_of: datetime
    merged_pr_throughput: ThroughputBreakdown
    median_pr_cycle_time: CycleTimePayload
    median_time_to_first_review: FirstReviewPayload


class DeliverySeriesResponse(BaseModel):
    weeks: int
    week_days: int
    slices: list[DeliveryResponse]


class EscapedDefectRow(BaseModel):
    release: str
    feature_prs: int
    bug_fix_prs: int
    docs_prs: int = Field(
        default=0,
        description="Merged documentation PRs in this milestone (denominator).",
    )
    escape_issues: int = Field(
        default=0,
        description="Issues with the escape label, attributed to this milestone "
        "(milestone on the issue is the *next* semver in repo order).",
    )
    rate: float | None = Field(
        default=None,
        description="escape_issues / (feature + bug_fix + docs); null if denominator is 0",
    )
    is_next_open: bool = Field(
        default=False,
        description="True for the lowest open semver milestone (pre-release / next target).",
    )


class EscapedDefectResponse(BaseModel):
    """Per-slice escaped defect stats (incremental in ``(window_start, window_end]``)."""

    window_start: datetime | None = None
    window_end: datetime | None = None
    as_of: datetime
    releases: list[EscapedDefectRow]


class EscapedDefectSeriesResponse(BaseModel):
    weeks: int
    week_days: int
    slices: list[EscapedDefectResponse]


class BugBacklogResponse(BaseModel):
    window_days: int
    window_start: datetime
    window_end: datetime
    as_of: datetime
    bugs_opened: int
    bugs_closed: int
    net: int


class BugBacklogSeriesResponse(BaseModel):
    weeks: int
    week_days: int
    slices: list[BugBacklogResponse]
