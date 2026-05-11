"""Offline CLI: fetch SDLC KPIs from GitHub and write a static HTML report.

Configuration uses the same environment variables as ``github_pm.context.Settings``:

* ``GITHUB_TOKEN`` (required) — personal access token with repo scope
* ``GITHUB_REPO`` — ``owner/name`` (default: ``vllm-project/guidellm``)
* ``SDLC_FEATURE_LABELS``, ``SDLC_BUG_LABELS``, ``SDLC_DOCS_LABELS``, ``SDLC_ESCAPE_LABEL`` — optional CSV label lists

CLI-specific optional env vars (overridden by flags when provided):

* ``SDLC_REPORT_WEEKS`` — number of weekly slices (default ``4``)
* ``SDLC_REPORT_WEEK_DAYS`` — days per slice (default ``7``)
* ``SDLC_REPORT_OUTPUT`` — default output path when ``--output`` is omitted

Generated-by: Cursor
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import click


@click.command()
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    envvar="SDLC_REPORT_OUTPUT",
    help="HTML file to write (default: sdlc-report.html in the current directory).",
)
@click.option(
    "--weeks",
    type=click.IntRange(1, 52),
    default=None,
    envvar="SDLC_REPORT_WEEKS",
    help="Number of rolling windows (default: 4, or SDLC_REPORT_WEEKS).",
)
@click.option(
    "--week-days",
    type=click.IntRange(1, 90),
    default=None,
    envvar="SDLC_REPORT_WEEK_DAYS",
    help="Length of each window in days (default: 7, or SDLC_REPORT_WEEK_DAYS).",
)
@click.option(
    "--repo",
    default=None,
    envvar="GITHUB_REPO",
    help="Override repository owner/name (otherwise from settings / GITHUB_REPO).",
)
def main(
    output: Path | None,
    weeks: int | None,
    week_days: int | None,
    repo: str | None,
) -> None:
    """Generate a static SDLC HTML report (same metrics as the /api/v1/sdlc REST API)."""
    from github_pm import sdlc_service
    from github_pm.api import Connector
    from github_pm.context import Settings
    from github_pm.sdlc_html_render import render_sdlc_report_html

    settings = Settings()
    if repo:
        settings = settings.model_copy(update={"github_repo": repo})

    token = (settings.github_token or "").strip()
    if not token:
        raise click.UsageError(
            "GitHub token is required. Set GITHUB_TOKEN in the environment "
            "(see github_pm.context.Settings)."
        )

    weeks_v = 4 if weeks is None else weeks
    days_v = 7 if week_days is None else week_days
    out = output if output is not None else Path.cwd() / "sdlc-report.html"

    gitctx = Connector(token, github_repo=settings.github_repo)
    delivery = sdlc_service.compute_sdlc_delivery_series(
        gitctx, settings, weeks=weeks_v, week_days=days_v
    )
    escaped = sdlc_service.compute_escaped_defect_rate_series(
        gitctx, settings, weeks=weeks_v, week_days=days_v
    )
    bugs = sdlc_service.compute_bug_backlog_delta_series(
        gitctx, settings, weeks=weeks_v, week_days=days_v
    )

    html_doc = render_sdlc_report_html(
        repo=settings.github_repo,
        generated_at=datetime.now(tz=UTC),
        delivery=delivery,
        escaped=escaped,
        bugs=bugs,
    )
    out.write_text(html_doc, encoding="utf-8")
    click.echo(f"Wrote {out.resolve()}")


if __name__ == "__main__":
    main()
