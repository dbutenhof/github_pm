"""Whole-interval SDLC collection with pure weekly aggregation.

Generated-by: Codex
"""

from datetime import datetime, timedelta

from github_pm import report_queries as rq
from github_pm import sdlc_metrics as sm
from github_pm.repository_catalog import milestone_catalog, VERSION_MATCH
from github_pm.sdlc_models import (
    BugBacklogResponse,
    BugBacklogSeriesResponse,
    DashboardResponse,
    DeliveryResponse,
    DeliverySeriesResponse,
    EscapedDefectResponse,
    EscapedDefectRow,
    EscapedDefectSeriesResponse,
)


def _post_graphql(gitctx):
    return lambda payload: gitctx.post("/graphql", payload)


def _range(field, start, end):
    # Search whole UTC dates, then enforce exact (start, end] timestamps locally.
    return f"{field}:{rq.date_str(start)}..{rq.date_str(end)}"


def _collect(gitctx, settings, start, end, kinds):
    post = _post_graphql(gitctx)
    repo = f"{gitctx.owner}/{gitctx.repo}"
    searches, facts = {}, {}
    if "delivery" in kinds:
        searches["merged"] = rq.Search(
            f'repo:{repo} is:pr is:merged {_range("merged", start, end)}', rq.DELIVERY
        )
        searches["opened"] = rq.Search(
            f'repo:{repo} is:pr {_range("created", start, end)}',
            rq.DELIVERY + " " + rq.REVIEWS,
        )
    if "escape" in kinds:
        opened_ms, closed_ms = milestone_catalog(gitctx)
        facts["targets"] = sm.select_escaped_defect_milestones(
            opened_ms, closed_ms, version_match=VERSION_MATCH
        )
        facts["previous"] = sm.build_semver_milestone_previous_map(
            opened_ms, closed_ms, version_match=VERSION_MATCH
        )
        searches["escapes"] = rq.Search(
            rq.escape_labeled_issues_query(repo, settings.sdlc_escape_label)
            + " "
            + _range("created", start, end),
            rq.ISSUE_DATES,
            "Issue",
        )
        if "delivery" not in kinds:
            for i, (title, _) in enumerate(facts["targets"]):
                searches[f"release{i}"] = rq.Search(
                    rq.milestone_merged_prs_query(repo, title)
                    + " "
                    + _range("merged", start, end),
                    rq.ESCAPE,
                )
    if "bugs" in kinds:
        searches["bugs_opened"] = rq.Search(
            rq.bug_issues_created_query_between(
                repo, settings.sdlc_bug_labels, start, end
            ),
            rq.ISSUE_DATES,
            "Issue",
        )
        searches["bugs_closed"] = rq.Search(
            rq.bug_issues_closed_query_between(
                repo, settings.sdlc_bug_labels, start, end
            ),
            rq.ISSUE_DATES,
            "Issue",
        )
    results = rq.search_many(post, searches)
    for key, nodes in results.items():
        if key in ("merged", "opened") or key.startswith("release"):
            rq.complete_prs(post, nodes, labels=True, reviews=key == "opened")
            rows = []
            for node in sm.filter_out_bot_pr_nodes(nodes):
                row = sm.pr_row_from_graphql_node(node, settings)
                if key == "opened":
                    reviews = [
                        dict(
                            user=dict(
                                login=(r.get("author") or {}).get("login"),
                                type=(r.get("author") or {}).get("__typename"),
                            ),
                            submitted_at=r.get("submittedAt"),
                        )
                        for r in node["reviews"]["nodes"]
                        if r
                    ]
                    row["first_review"] = sm.first_human_review_submitted_at(reviews)
                rows.append(row)
            facts[key] = rows
        else:
            facts[key] = nodes
    if "escape" in kinds and "delivery" not in kinds:
        facts["merged"] = [
            row
            for key, rows in facts.items()
            if key.startswith("release")
            for row in rows
        ]
    return facts


def _inside(value, start, end):
    return value is not None and start < value <= end


def _delivery(facts, start, end, days):
    merged = [r for r in facts["merged"] if _inside(r["merged_at"], start, end)]
    opened = [r for r in facts["opened"] if _inside(r["created_at"], start, end)]
    reviewed = [
        (r, max(0.0, (r["first_review"] - r["created_at"]).total_seconds()))
        for r in opened
        if r.get("first_review")
    ]
    return DeliveryResponse(
        window_days=days,
        window_start=start,
        window_end=end,
        as_of=end,
        merged_pr_throughput=sm.aggregate_throughput(merged),
        median_pr_cycle_time=sm.build_median_cycle_payload(merged),
        median_time_to_first_review=sm.build_first_review_payload(
            reviewed, eligible_count=len(opened)
        ),
    )


def _escape(facts, start, end):
    releases = []
    for title, next_open in facts["targets"]:
        rows = [
            r
            for r in facts["merged"]
            if r["milestone_title"] == title
            and (start is None or _inside(r["merged_at"], start, end))
        ]
        counts = {
            kind: sum(r["pr_type"] == kind for r in rows)
            for kind in ("feature", "bug_fix", "docs")
        }
        escapes = sum(
            facts["previous"].get((i.get("milestone") or {}).get("title")) == title
            and (
                start is None
                or _inside(sm.parse_github_ts(i.get("createdAt")), start, end)
            )
            for i in facts["escapes"]
        )
        denominator = sum(counts.values())
        releases.append(
            EscapedDefectRow(
                release=title,
                feature_prs=counts["feature"],
                bug_fix_prs=counts["bug_fix"],
                docs_prs=counts["docs"],
                escape_issues=escapes,
                rate=escapes / denominator if denominator else None,
                is_next_open=next_open,
            )
        )
    return EscapedDefectResponse(
        window_start=start,
        window_end=end if start is not None else None,
        as_of=end,
        releases=releases,
    )


def _bugs(facts, start, end, days):
    opened = sum(
        _inside(sm.parse_github_ts(n.get("createdAt")), start, end)
        for n in facts["bugs_opened"]
    )
    closed = sum(
        _inside(sm.parse_github_ts(n.get("closedAt")), start, end)
        for n in facts["bugs_closed"]
    )
    return BugBacklogResponse(
        window_days=days,
        window_start=start,
        window_end=end,
        as_of=end,
        bugs_opened=opened,
        bugs_closed=closed,
        net=opened - closed,
    )


def _series(facts, now, weeks, week_days, kind):
    slices = []
    for i in reversed(range(weeks)):
        end = now - timedelta(days=i * week_days)
        start = end - timedelta(days=week_days)
        if kind == "delivery":
            slices.append(_delivery(facts, start, end, week_days))
        elif kind == "escape":
            slices.append(_escape(facts, start, end))
        else:
            slices.append(_bugs(facts, start, end, week_days))
    model = {
        "delivery": DeliverySeriesResponse,
        "escape": EscapedDefectSeriesResponse,
        "bugs": BugBacklogSeriesResponse,
    }[kind]
    return model(weeks=weeks, week_days=week_days, slices=slices)


def compute_sdlc_dashboard(gitctx, settings, *, weeks=4, week_days=7):
    now = sm.utc_now()
    kinds = {"delivery", "escape", "bugs"}
    facts = _collect(
        gitctx, settings, now - timedelta(days=weeks * week_days), now, kinds
    )
    return DashboardResponse(
        delivery=_series(facts, now, weeks, week_days, "delivery"),
        escaped=_series(facts, now, weeks, week_days, "escape"),
        backlog=_series(facts, now, weeks, week_days, "bugs"),
    )


def _standalone(gitctx, settings, weeks, week_days, kind, now=None):
    now = now or sm.utc_now()
    facts = _collect(
        gitctx, settings, now - timedelta(days=weeks * week_days), now, {kind}
    )
    return _series(facts, now, weeks, week_days, kind)


def compute_sdlc_delivery_series(gitctx, settings, *, weeks, week_days=7):
    return _standalone(gitctx, settings, weeks, week_days, "delivery")


def compute_sdlc_delivery(gitctx, settings, *, days=7, now: datetime | None = None):
    return _standalone(gitctx, settings, 1, days, "delivery", now).slices[0]


def compute_escaped_defect_rate_series(gitctx, settings, *, weeks, week_days=7):
    return _standalone(gitctx, settings, weeks, week_days, "escape")


def compute_bug_backlog_delta_series(gitctx, settings, *, weeks, week_days=7):
    return _standalone(gitctx, settings, weeks, week_days, "bugs")


def compute_bug_backlog_delta(gitctx, settings, *, days=7, now=None):
    return _standalone(gitctx, settings, 1, days, "bugs", now).slices[0]


def compute_escaped_defect_rate(gitctx, settings):
    """Cumulative metrics deliberately retain their unbounded historical scope."""
    repo = f"{gitctx.owner}/{gitctx.repo}"
    opened, closed = milestone_catalog(gitctx)
    facts = {
        "targets": sm.select_escaped_defect_milestones(
            opened, closed, version_match=VERSION_MATCH
        ),
        "previous": sm.build_semver_milestone_previous_map(
            opened, closed, version_match=VERSION_MATCH
        ),
    }
    historical_scope = f" created:1970-01-01..{rq.date_str(sm.utc_now())}"
    searches = {
        "escapes": rq.Search(
            rq.escape_labeled_issues_query(repo, settings.sdlc_escape_label)
            + historical_scope,
            rq.ISSUE_DATES,
            "Issue",
        )
    }
    for i, (title, _) in enumerate(facts["targets"]):
        searches[f"release{i}"] = rq.Search(
            rq.milestone_merged_prs_query(repo, title) + historical_scope, rq.ESCAPE
        )
    post = _post_graphql(gitctx)
    results = rq.search_many(post, searches)
    facts["escapes"], facts["merged"] = results.pop("escapes"), []
    for nodes in results.values():
        rq.complete_prs(post, nodes, labels=True)
        facts["merged"].extend(
            sm.pr_row_from_graphql_node(n, settings)
            for n in sm.filter_out_bot_pr_nodes(nodes)
        )
    return _escape(facts, None, sm.utc_now())
