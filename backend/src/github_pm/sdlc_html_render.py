"""Static HTML report for SDLC KPI payloads (offline-friendly).

Generated-by: Cursor
"""

from __future__ import annotations

import html
from datetime import UTC, datetime
from typing import Any

from github_pm.sdlc_models import (
    BugBacklogSeriesResponse,
    DeliverySeriesResponse,
    EscapedDefectSeriesResponse,
)


def _esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def format_duration_seconds(secs: float | None) -> str:
    """Human-readable duration for median seconds (or em dash if unknown)."""
    if secs is None:
        return "—"
    if secs < 0:
        return "—"
    total = int(round(secs))
    if total < 60:
        return f"{total}s"
    m, s = divmod(total, 60)
    if m < 60:
        return f"{m}m {s}s" if s else f"{m}m"
    h, m = divmod(m, 60)
    if h < 48:
        parts = [f"{h}h"]
        if m:
            parts.append(f"{m}m")
        return " ".join(parts)
    d, h = divmod(h, 24)
    parts = [f"{d}d"]
    if h:
        parts.append(f"{h}h")
    return " ".join(parts)


def _dt_utc_iso(d: datetime) -> str:
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    else:
        d = d.astimezone(UTC)
    return d.strftime("%Y-%m-%d %H:%M UTC")


def _pr_type_label(key: str) -> str:
    return {
        "feature": "Feature",
        "bug_fix": "Bug fix",
        "docs": "Docs",
        "unclassified": "Unclassified",
    }.get(key, key.replace("_", " ").title())


def _size_label(key: str) -> str:
    return key.replace("_", " ").title()


def _fmt_pct(rate: float | None) -> str:
    if rate is None:
        return "—"
    return f"{100.0 * rate:.1f}%"


def render_sdlc_report_html(
    *,
    repo: str,
    generated_at: datetime,
    delivery: DeliverySeriesResponse,
    escaped: EscapedDefectSeriesResponse,
    bugs: BugBacklogSeriesResponse,
) -> str:
    """Build a single self-contained HTML document (no external assets)."""
    title = f"SDLC — {_esc(repo)}"
    rows_delivery: list[str] = []
    for sl in delivery.slices:
        tp = sl.merged_pr_throughput
        type_bits = ", ".join(
            f"{_pr_type_label(k)}: {v}" for k, v in sorted(tp.by_pr_type.items())
        )
        rows_delivery.append(
            "<tr>"
            f"<td>{_esc(_dt_utc_iso(sl.window_end))}</td>"
            f"<td class='num'>{tp.total}</td>"
            f"<td>{_esc(type_bits)}</td>"
            f"<td class='num'>{_esc(format_duration_seconds(sl.median_pr_cycle_time.median_seconds))}</td>"
            f"<td class='num'>{_esc(format_duration_seconds(sl.median_time_to_first_review.median_seconds))}</td>"
            f"<td class='num'>{sl.median_time_to_first_review.included_pr_count}/"
            f"{sl.median_time_to_first_review.eligible_pr_count}</td>"
            "</tr>"
        )

    rows_escape: list[str] = []
    for sl in escaped.slices:
        slice_end = sl.window_end if sl.window_end is not None else sl.as_of
        wk = _esc(_dt_utc_iso(slice_end))
        if not sl.releases:
            rows_escape.append(
                f"<tr><td colspan='7' class='muted'>{wk} — no milestone rows</td></tr>"
            )
            continue
        for rel in sl.releases:
            tag = " <span class='pill'>next</span>" if rel.is_next_open else ""
            rows_escape.append(
                "<tr>"
                f"<td>{wk}</td>"
                f"<td>{_esc(rel.release)}{tag}</td>"
                f"<td class='num'>{rel.feature_prs}</td>"
                f"<td class='num'>{rel.bug_fix_prs}</td>"
                f"<td class='num'>{rel.docs_prs}</td>"
                f"<td class='num'>{rel.escape_issues}</td>"
                f"<td class='num'>{_esc(_fmt_pct(rel.rate))}</td>"
                "</tr>"
            )

    rows_bugs: list[str] = []
    for sl in bugs.slices:
        rows_bugs.append(
            "<tr>"
            f"<td>{_esc(_dt_utc_iso(sl.window_end))}</td>"
            f"<td class='num'>{sl.bugs_opened}</td>"
            f"<td class='num'>{sl.bugs_closed}</td>"
            f"<td class='num'>{sl.net:+d}</td>"
            "</tr>"
        )

    if delivery.slices:
        last = delivery.slices[-1]
        cycle_breakdown = _breakdown_section(
            "Median PR cycle time by type / size (latest week)",
            last.median_pr_cycle_time,
        )
        review_breakdown = _breakdown_section(
            "Median time to first human review by type / size (latest week)",
            last.median_time_to_first_review,
        )
    else:
        cycle_breakdown = _empty_breakdown_section(
            "Median PR cycle time by type / size (latest week)"
        )
        review_breakdown = _empty_breakdown_section(
            "Median time to first human review by type / size (latest week)"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <style>
    :root {{
      --bg: #0d1117;
      --surface: #161b22;
      --border: #30363d;
      --text: #e6edf3;
      --muted: #8b949e;
      --accent: #58a6ff;
      --pos: #3fb950;
      --neg: #f85149;
    }}
    body {{
      font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 1.5rem;
      line-height: 1.45;
    }}
    .wrap {{ max-width: 1200px; margin: 0 auto; }}
    header {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 1rem;
      margin-bottom: 1.5rem;
    }}
    h1 {{ font-size: 1.35rem; font-weight: 600; margin: 0 0 0.35rem 0; }}
    .sub {{ color: var(--muted); font-size: 0.9rem; }}
    section {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.1rem;
      margin-bottom: 1.25rem;
    }}
    h2 {{
      font-size: 1.05rem;
      font-weight: 600;
      margin: 0 0 0.75rem 0;
      color: var(--accent);
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    th, td {{ text-align: left; padding: 0.45rem 0.5rem; border-bottom: 1px solid var(--border); vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 500; font-size: 0.82rem; }}
    tr:last-child td {{ border-bottom: none; }}
    td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .muted {{ color: var(--muted); }}
    .pill {{
      display: inline-block;
      font-size: 0.7rem;
      padding: 0.1rem 0.35rem;
      border-radius: 999px;
      background: #21262d;
      color: var(--accent);
      border: 1px solid var(--border);
      margin-left: 0.25rem;
    }}
    .grid2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }}
    @media (max-width: 800px) {{
      .grid2 {{ grid-template-columns: 1fr; }}
    }}
    .kv {{ font-size: 0.85rem; color: var(--muted); }}
    .kv code {{ color: var(--text); }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>SDLC metrics</h1>
      <div class="sub">Repository <strong>{_esc(repo)}</strong> · Generated {_esc(_dt_utc_iso(generated_at))}</div>
      <p class="kv">Rolling windows: <code>{delivery.weeks}</code> slices × <code>{delivery.week_days}</code> days (UTC, oldest → newest in tables).</p>
    </header>

    <section>
      <h2>Delivery</h2>
      <p class="muted" style="margin-top:0">Merged PR throughput, median cycle time, median time to first human review (bots excluded).</p>
      <table>
        <thead>
          <tr>
            <th>Week ending</th>
            <th class="num">Merged PRs</th>
            <th>By PR type</th>
            <th class="num">Median cycle</th>
            <th class="num">Median first review</th>
            <th class="num">PRs w/ review</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows_delivery)}
        </tbody>
      </table>
    </section>

    <div class="grid2">
      {cycle_breakdown}
      {review_breakdown}
    </div>

    <section>
      <h2>Escaped defect rate (weekly incremental)</h2>
      <p class="muted" style="margin-top:0">Per milestone row: merged PR counts in the window and escape-labeled issues created in the window (attributed by milestone), same semantics as the API.</p>
      <table>
        <thead>
          <tr>
            <th>Slice end</th>
            <th>Release</th>
            <th class="num">Features</th>
            <th class="num">Bug fixes</th>
            <th class="num">Docs</th>
            <th class="num">Escapes</th>
            <th class="num">Rate</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows_escape)}
        </tbody>
      </table>
    </section>

    <section>
      <h2>Bug backlog delta</h2>
      <p class="muted" style="margin-top:0">Issues matching configured bug labels: opened vs closed in each window.</p>
      <table>
        <thead>
          <tr>
            <th>Week ending</th>
            <th class="num">Opened</th>
            <th class="num">Closed</th>
            <th class="num">Net</th>
          </tr>
        </thead>
        <tbody>
          {"".join(rows_bugs)}
        </tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""


def _empty_breakdown_section(title: str) -> str:
    return f"""
    <section>
      <h2>{_esc(title)}</h2>
      <p class="muted">No delivery data for this report.</p>
    </section>
    """


def _breakdown_section(title: str, payload: Any) -> str:
    """Render by_pr_type and by_pr_size tables for cycle or first-review payload."""
    rows_t = "".join(
        f"<tr><td>{_esc(_pr_type_label(k))}</td><td class='num'>{_esc(format_duration_seconds(v))}</td></tr>"
        for k, v in sorted(payload.by_pr_type.items())
    )
    rows_s = "".join(
        f"<tr><td>{_esc(_size_label(k))}</td><td class='num'>{_esc(format_duration_seconds(v))}</td></tr>"
        for k, v in sorted(payload.by_pr_size.items())
    )
    median = format_duration_seconds(payload.median_seconds)
    return f"""
    <section>
      <h2>{_esc(title)}</h2>
      <p class="muted">Overall median: <strong>{_esc(median)}</strong></p>
      <table>
        <thead><tr><th>PR type</th><th class="num">Median</th></tr></thead>
        <tbody>{rows_t}</tbody>
      </table>
      <table style="margin-top:0.75rem">
        <thead><tr><th>PR size</th><th class="num">Median</th></tr></thead>
        <tbody>{rows_s}</tbody>
      </table>
    </section>
    """
