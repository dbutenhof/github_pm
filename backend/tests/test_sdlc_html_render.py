"""Tests for SDLC static HTML rendering.

Generated-by: Cursor
"""

from datetime import UTC, datetime, timedelta

from github_pm.sdlc_html_render import format_duration_seconds, render_sdlc_report_html
from github_pm.sdlc_models import (
    BugBacklogResponse,
    BugBacklogSeriesResponse,
    CycleTimePayload,
    DeliveryResponse,
    DeliverySeriesResponse,
    EscapedDefectResponse,
    EscapedDefectRow,
    EscapedDefectSeriesResponse,
    FirstReviewPayload,
    ThroughputBreakdown,
)


def test_format_duration_seconds():
    assert format_duration_seconds(None) == "—"
    assert format_duration_seconds(45.0) == "45s"
    assert format_duration_seconds(120.0) == "2m"
    assert format_duration_seconds(3720.0) == "1h 2m"


def test_render_sdlc_report_html_contains_sections():
    t0 = datetime(2025, 4, 3, 12, 0, 0, tzinfo=UTC)
    t1 = datetime(2025, 4, 10, 12, 0, 0, tzinfo=UTC)
    delivery = DeliverySeriesResponse(
        weeks=1,
        week_days=7,
        slices=[
            DeliveryResponse(
                window_days=7,
                window_start=t0,
                window_end=t1,
                as_of=t1,
                merged_pr_throughput=ThroughputBreakdown(
                    total=1,
                    by_pr_type={"feature": 1},
                    by_pr_size={"small": 1},
                ),
                median_pr_cycle_time=CycleTimePayload(
                    median_seconds=86400.0,
                    by_pr_type={"feature": 86400.0},
                    by_pr_size={"small": 86400.0},
                    pr_count=1,
                ),
                median_time_to_first_review=FirstReviewPayload(
                    median_seconds=3600.0,
                    by_pr_type={"feature": 3600.0},
                    by_pr_size={"small": 3600.0},
                    included_pr_count=1,
                    eligible_pr_count=2,
                ),
            )
        ],
    )
    escaped = EscapedDefectSeriesResponse(
        weeks=1,
        week_days=7,
        slices=[
            EscapedDefectResponse(
                window_start=t0,
                window_end=t1,
                as_of=t1,
                releases=[
                    EscapedDefectRow(
                        release="v0.1.0",
                        feature_prs=1,
                        bug_fix_prs=0,
                        docs_prs=0,
                        escape_issues=0,
                        rate=0.0,
                        is_next_open=True,
                    )
                ],
            )
        ],
    )
    bugs = BugBacklogSeriesResponse(
        weeks=1,
        week_days=7,
        slices=[
            BugBacklogResponse(
                window_days=7,
                window_start=t0,
                window_end=t1,
                as_of=t1,
                bugs_opened=2,
                bugs_closed=1,
                net=1,
            )
        ],
    )
    html = render_sdlc_report_html(
        repo="o/r",
        generated_at=t1 + timedelta(hours=1),
        delivery=delivery,
        escaped=escaped,
        bugs=bugs,
    )
    assert "<!DOCTYPE html>" in html
    assert "SDLC metrics" in html
    assert "o/r" in html
    assert "Delivery" in html
    assert "Escaped defect" in html
    assert "Bug backlog" in html
    assert "v0.1.0" in html
    assert "1d" in html or "24h" in html  # median cycle in breakdown
