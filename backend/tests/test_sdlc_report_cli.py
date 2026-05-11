"""Tests for the offline SDLC HTML report CLI.

Generated-by: Cursor
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner


def _have_fastapi() -> bool:
    return importlib.util.find_spec("fastapi") is not None


pytestmark = pytest.mark.skipif(
    not _have_fastapi(),
    reason="SDLC report CLI tests require project dependencies (fastapi).",
)

from github_pm.sdlc_models import (
    BugBacklogResponse,
    BugBacklogSeriesResponse,
    CycleTimePayload,
    DeliveryResponse,
    DeliverySeriesResponse,
    EscapedDefectResponse,
    EscapedDefectSeriesResponse,
    FirstReviewPayload,
    ThroughputBreakdown,
)


def _minimal_series():
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
                    total=0, by_pr_type={}, by_pr_size={}
                ),
                median_pr_cycle_time=CycleTimePayload(
                    median_seconds=None,
                    by_pr_type={},
                    by_pr_size={},
                    pr_count=0,
                ),
                median_time_to_first_review=FirstReviewPayload(
                    median_seconds=None,
                    by_pr_type={},
                    by_pr_size={},
                    included_pr_count=0,
                    eligible_pr_count=0,
                ),
            )
        ],
    )
    escaped = EscapedDefectSeriesResponse(
        weeks=1,
        week_days=7,
        slices=[EscapedDefectResponse(as_of=t1, releases=[])],
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
                bugs_opened=0,
                bugs_closed=0,
                net=0,
            )
        ],
    )
    return delivery, escaped, bugs


class TestSdlcReportCli:
    def test_requires_token(self, tmp_path: Path):
        from github_pm.sdlc_report_cli import main

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--output", str(tmp_path / "out.html")],
            env={
                "GITHUB_TOKEN": "",
                "GITHUB_REPO": "a/b",
            },
        )
        assert result.exit_code != 0
        out = (getattr(result, "stdout", "") or "") + (
            getattr(result, "stderr", "") or ""
        )
        assert "token" in out.lower()

    def test_writes_html(self, tmp_path: Path):
        from github_pm.sdlc_report_cli import main

        delivery, escaped, bugs = _minimal_series()
        out = tmp_path / "report.html"

        with (
            patch("github_pm.api.Connector") as mc,
            patch(
                "github_pm.sdlc_service.compute_sdlc_delivery_series",
                return_value=delivery,
            ),
            patch(
                "github_pm.sdlc_service.compute_escaped_defect_rate_series",
                return_value=escaped,
            ),
            patch(
                "github_pm.sdlc_service.compute_bug_backlog_delta_series",
                return_value=bugs,
            ),
        ):
            mc.return_value = object()
            runner = CliRunner()
            result = runner.invoke(
                main,
                ["--output", str(out), "--weeks", "1"],
                env={"GITHUB_TOKEN": "tok", "GITHUB_REPO": "x/y"},
            )

        assert result.exit_code == 0, result.output
        assert out.is_file()
        body = out.read_text(encoding="utf-8")
        assert "SDLC metrics" in body
        assert "x/y" in body
