"""Pydantic models for the weekly project status report API.

Generated-by: Cursor
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class StatusReportItem(BaseModel):
    """A GitHub issue or pull request row for the status UI."""

    number: int = Field(description="Issue or PR number")
    title: str = Field(description="Title")
    html_url: str = Field(description="GitHub HTML URL for the issue or PR")


class PrBacklogItem(StatusReportItem):
    """Open stale PR row including age relative to the report ``end_date``."""

    days_since_update: int = Field(
        ge=0,
        description=(
            "Whole calendar days from the PR's last ``updatedAt`` (UTC date) through "
            "``end_date`` (inclusive), matching the report window's last day"
        ),
    )


class ProjectStatusReportResponse(BaseModel):
    """Inclusive calendar window from ``start_date`` through ``end_date`` (UTC calendar dates)."""

    start_date: date = Field(description="First calendar day of the window (inclusive)")
    end_date: date = Field(description="Last calendar day of the window (inclusive)")
    merged_pull_requests: list[StatusReportItem] = Field(
        default_factory=list,
        description="Pull requests merged in the window (by merge date)",
    )
    opened_pull_requests: list[StatusReportItem] = Field(
        default_factory=list,
        description="Pull requests created in the window",
    )
    opened_issues: list[StatusReportItem] = Field(
        default_factory=list,
        description="Issues created in the window (pull requests excluded)",
    )
    recently_updated_pull_requests: list[StatusReportItem] = Field(
        default_factory=list,
        description=(
            "Open, non-draft pull requests updated in the window whose ``createdAt`` "
            "UTC calendar date is outside the window (not newly opened this period)"
        ),
    )
    reviewer_attention_needed: list[StatusReportItem] = Field(
        default_factory=list,
        description=(
            "Open, non-draft PRs with ``mergeable`` MERGEABLE and a clean branch "
            "(``mergeStateStatus`` not BEHIND or DIRTY), with no submitted review or "
            "``updatedAt`` after the latest review ``submittedAt``"
        ),
    )
    creator_attention_needed: list[StatusReportItem] = Field(
        default_factory=list,
        description=(
            "Open PRs (including drafts) that need branch work or author follow-up: "
            "``mergeable`` CONFLICTING, ``mergeStateStatus`` BEHIND or DIRTY, or latest "
            "submitted review newer than ``updatedAt``"
        ),
    )
    pr_backlog: list[PrBacklogItem] = Field(
        default_factory=list,
        description=(
            "Open, non-draft pull requests whose last update (UTC) is strictly before "
            "start_date — not merged or closed, stale since the report window began"
        ),
    )
