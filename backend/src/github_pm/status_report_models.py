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
