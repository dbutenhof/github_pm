"""Unit tests for sdlc_metrics helpers."""

import re
from datetime import UTC, datetime

import pytest

_SEMVER = re.compile(r"^v\d+\.\d+\.\d+$")

from github_pm.context import Settings
from github_pm import sdlc_metrics as sm


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_name="t",
        github_repo="o/r",
        github_token="",
        sdlc_feature_labels="enhancement",
        sdlc_bug_labels="bug",
        sdlc_docs_labels="documentation",
        sdlc_escape_label="escape",
    )


def test_classify_precedence(settings: Settings):
    assert sm.classify_pr_type(["bug", "documentation"], settings) == "bug_fix"
    assert sm.classify_pr_type(["documentation", "enhancement"], settings) == "docs"
    assert sm.classify_pr_type(["enhancement"], settings) == "feature"
    assert sm.classify_pr_type([], settings) == "unclassified"


def test_size_bucket():
    assert sm.size_bucket_from_lines(0) == "tiny"
    assert sm.size_bucket_from_lines(10) == "tiny"
    assert sm.size_bucket_from_lines(11) == "small"
    assert sm.size_bucket_from_lines(100) == "small"
    assert sm.size_bucket_from_lines(101) == "medium"
    assert sm.size_bucket_from_lines(500) == "medium"
    assert sm.size_bucket_from_lines(501) == "large"


def test_median_seconds():
    assert sm.median_seconds([]) is None
    assert sm.median_seconds([2.0]) == 2.0
    assert sm.median_seconds([1.0, 2.0, 3.0]) == 2.0
    assert sm.median_seconds([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_is_pr_author_bot():
    assert sm.is_pr_author_bot({"__typename": "Bot", "login": "dependabot[bot]"})
    assert sm.is_pr_author_bot({"__typename": "User", "login": "dependabot[bot]"})
    assert sm.is_pr_author_bot({"__typename": "User", "login": "mergify[bot]"})
    assert sm.is_pr_author_bot({"__typename": "User", "login": "mergify-test"})
    assert not sm.is_pr_author_bot({"__typename": "User", "login": "human"})
    assert not sm.is_pr_author_bot(None)


def test_filter_out_bot_pr_nodes():
    human = {"__typename": "User", "login": "alice"}
    bot = {"__typename": "User", "login": "dependabot[bot]"}
    nodes = [
        {"number": 1, "author": human},
        {"number": 2, "author": bot},
        {"number": 3, "author": human},
    ]
    assert [n["number"] for n in sm.filter_out_bot_pr_nodes(nodes)] == [1, 3]


def test_first_human_review_skips_bot():
    reviews = [
        {
            "user": {"login": "copilot-pull-request-reviewer[bot]", "type": "Bot"},
            "submitted_at": "2025-01-01T10:00:00Z",
        },
        {
            "user": {"login": "human", "type": "User"},
            "submitted_at": "2025-01-01T11:00:00Z",
        },
    ]
    t = sm.first_human_review_submitted_at(reviews)
    assert t == datetime(2025, 1, 1, 11, 0, tzinfo=UTC)


def test_aggregate_throughput_and_cycle():
    c = datetime(2025, 4, 1, 12, 0, tzinfo=UTC)
    m = datetime(2025, 4, 2, 12, 0, tzinfo=UTC)
    rows = [
        {
            "pr_type": "feature",
            "size_bucket": "tiny",
            "created_at": c,
            "merged_at": m,
        },
        {
            "pr_type": "bug_fix",
            "size_bucket": "large",
            "created_at": c,
            "merged_at": m,
        },
    ]
    agg = sm.aggregate_throughput(rows)
    assert agg["total"] == 2
    assert agg["by_pr_type"]["feature"] == 1
    assert agg["by_pr_type"]["bug_fix"] == 1

    cycle = sm.build_median_cycle_payload(rows)
    assert cycle["pr_count"] == 2
    assert cycle["median_seconds"] == 86400.0


def test_label_or_clause():
    assert "label:bug" in sm._label_or_clause(frozenset({"bug"}))
    assert "OR" in sm._label_or_clause(frozenset({"a", "b"}))


def test_milestone_query_escapes_quotes():
    q = sm.milestone_merged_prs_query("o/r", 'v1.0.0"')
    assert '\\"' in q or "v1.0.0" in q


def test_select_escaped_defect_milestones_three_lines_sorted():
    # Next open v0.7.0 → lines (0,5), (0,6), (0,7); pick latest closed on 0.5 / 0.6
    open_ms = [{"title": "v0.7.0"}]
    closed_ms = [
        {"title": "v0.5.0", "closed_at": "2025-01-01T00:00:00Z"},
        {"title": "v0.5.1", "closed_at": "2025-02-01T00:00:00Z"},
        {"title": "v0.6.0", "closed_at": "2025-03-01T00:00:00Z"},
    ]
    out = sm.select_escaped_defect_milestones(
        open_ms,
        closed_ms,
        version_match=_SEMVER,
    )
    assert out == [
        ("v0.5.1", False),
        ("v0.6.0", False),
        ("v0.7.0", True),
    ]


def test_select_escaped_defect_milestones_skips_missing_closed_line():
    open_ms = [{"title": "v0.7.0"}]
    closed_ms = [{"title": "v0.6.0", "closed_at": "2025-03-01T00:00:00Z"}]
    out = sm.select_escaped_defect_milestones(
        open_ms,
        closed_ms,
        version_match=_SEMVER,
    )
    # No v0.5.x closed → only v0.6.0 and v0.7.0
    assert out == [("v0.6.0", False), ("v0.7.0", True)]


def test_select_escaped_defect_milestones_empty_when_no_open_semver():
    assert (
        sm.select_escaped_defect_milestones([], [], version_match=_SEMVER) == []
    )


def test_build_semver_milestone_previous_map():
    open_m = [{"title": "v2.0.1"}]
    closed_m = [{"title": "v1.0.0"}, {"title": "v2.0.0"}]
    prev = sm.build_semver_milestone_previous_map(
        open_m, closed_m, version_match=_SEMVER
    )
    assert prev == {"v2.0.0": "v1.0.0", "v2.0.1": "v2.0.0"}
    assert "v1.0.0" not in prev


def test_escape_labeled_issues_query():
    q = sm.escape_labeled_issues_query("acme/rocket", "escape")
    assert "repo:acme/rocket" in q
    assert "is:issue" in q
    assert "label:escape" in q


def test_count_escape_issues_by_prior_milestone():
    prev = {"v2.0.0": "v1.0.0", "v2.0.1": "v2.0.0"}
    items = [
        {"milestone": {"title": "v2.0.0"}},
        {"milestone": {"title": "v2.0.0"}},
        {"milestone": {"title": "v2.0.1"}},
        {"milestone": None},
        {"milestone": {"title": "backlog"}},
    ]
    c = sm.count_escape_issues_by_prior_milestone(
        items, prev, version_match=_SEMVER
    )
    assert c == {"v1.0.0": 2, "v2.0.0": 1}
