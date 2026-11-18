**GitHub API efficiency investigation — 2026-11-18**

Implementation is now complete; see [implementation and validation notes](github-api-optimization-implementation.md). The following investigation describes the original `a49ea37` baseline, so its source line references and current-behavior descriptions are historical.

Reviewed branch `optimize`, commit `a49ea37`. The worktree was clean at the start. This is a static analysis of the frontend, backend, and relevant tests, with GitHub/FastAPI documentation checks. Request counts below are derived from control flow, exclude retries unless stated, and are not measured latency results. No authenticated GitHub requests or application changes were made.

**Recommendation**

There is substantial room to reduce GitHub requests while retaining the UI. The largest gains come from batching Planning enrichment, fetching SDLC data once for the whole reporting interval, and reusing the open-PR dataset within Project Status. Keep REST where it already performs a focused operation efficiently. Separate consumer-specific data selection from reusable transport and computation.

| Priority | Change | Expected benefit | Main preservation concern |
| --- | --- | --- | --- |
| First | Batch Planning issue enrichment | Eliminate one GraphQL round trip per issue | Hierarchy, dependencies, closing PRs, complete pagination |
| First | Load one SDLC interval and partition locally; include reviews in GraphQL | Eliminate repeated overlapping searches and per-PR REST review calls | Exact time windows, bot filters, review semantics, size/type breakdowns |
| First | Move blocking HTTP work out of async route execution | Keep unrelated UI requests responsive during reports | Bound GitHub traffic; preserve errors and cancellation behavior |
| First | Stop reaction retry loops | Prevent repeated requests after failure or an empty response | Preserve reactor names and retry after explicit refresh |
| Next | Reuse Project Status open PRs; tailor its fields | Six logical searches become four; batch independent first pages | Current-state attention versus date-window sections |
| Next | Use focused REST label operations; larger REST pages | Halve ordinary label-change calls; fewer list pages | Duplicate/missing-label behavior and concurrent edits |
| Next | Use GraphQL milestone counts; sort loaded issues locally | Avoid full item downloads for counts or sort changes | Separate issue/PR counts and sibling ordering |
| Later | Consolidate metadata caches and lazy detail loading | Reduce duplicate, hidden, and remount-related work | Explicit freshness, editing, external changes |
| Later | Reuse hierarchy traversal during mutations | Reduce subtree reads during drag/drop and adoption | Closed descendants, cycle checks, partial failure |

**Current UI-to-GitHub request map**

All backend paths below are under `/api/v1`. `P30(n) = max(1, ceil(n/30))` describes an ordinary REST list with the default page size; `G(q)` is the number of GraphQL pages for query `q`.

| UI action | Frontend / backend entry points | Current GitHub work |
| --- | --- | --- |
| Application mount | `App.jsx:88`, `App.jsx:100`; `/project`, `/milestones`, `/labels`, `/assignees` | Project is local configuration. Three independent paginated REST lists preload regardless of active tab. |
| Expand milestone | `MilestoneCard.jsx:158`; `api.py:296` | REST list of open issues and PRs, then one sequential hierarchy GraphQL request per non-PR issue. |
| Change label sort | `MilestoneCard.jsx:183` | Reloads the same milestone data and repeats enrichment for expanded, previously loaded cards. |
| Planning Refresh | `App.jsx:243`, `MilestoneCard.jsx:197` | Reloads every previously loaded card, including collapsed ones; unopened cards remain lazy. |
| Issue reactions | `IssueCard.jsx:337`; `api.py:674` | Paginated REST reactions for each mounted row whose reaction summary is nonzero, even while its description is collapsed. |
| Expand comments | `IssueCard.jsx:241`; `api.py:393` | Paginated REST comments, followed by a separate reaction request per comment with reactions. |
| Close milestone confirmation | `ManageMilestones.jsx:182`; `api.py:784` | Downloads all open items with raw and rendered bodies just to count issues and PRs separately. |
| Project Status Apply | `ProjectStatusPanel.jsx:182`; `status_report_service.py:170` | Six sequential GraphQL searches: merged PRs, opened PRs, opened issues, updated open PRs, all open PRs with reviews, stale open PRs. |
| SDLC tab / week change | `SdlcKpisPanel.jsx:265`; `sdlc_api.py` | Three browser requests via `Promise.all`; separate delivery, escape, and backlog collectors. |
| Label toggle | `IssueCard.jsx:722`; `api.py:1385` | GET issue, then PATCH the complete label set when a change is needed. |
| Reparent across milestones | `api.py:913` | Traverse descendants for cycle check, fetch child and parent, link, traverse the same subtree again, PATCH root and every descendant. |

The frontend already avoids some unnecessary work: comments are lazy, unopened milestones are lazy, shared metadata promises deduplicate several loads, and many mutations update local state without a full reload. Preserve those advantages.

**1. Planning: retain the useful REST list and batch its enrichment**

Evidence: `backend/src/github_pm/api.py:296`, `backend/src/github_pm/issue_hierarchy.py:128`, `frontend/src/components/MilestoneCard.jsx:158`.

For `I` issues and `R` PRs, initial loading currently costs `P30(I + R) + I` requests before any reactions. All enrichment requests are sequential. A milestone containing 100 issues and no PRs therefore requires 104 GitHub requests.

A focused first implementation would retain the REST list, request `per_page=100`, collect issue `node_id` values, and enrich them in configurable GraphQL batches. GitHub supports lookup of multiple nodes by ID; aliases of `repository.issue(number:)` are an alternative when numbers are the available identity. Map results by identity, preserving errors and missing nodes per item. [GitHub node lookup](https://docs.github.com/en/graphql/reference/meta#nodes).

With an illustrative batch size of 50 and no nested overflow, that 100-issue example becomes one REST request plus two GraphQL requests: **104 → 3**. Batch size 50 is a tuning starting point, not a GitHub requirement or a demonstrated optimum. Extra pages for linked collections increase this count.

The current hierarchy fragment also fetches `subIssues(first:100)`, but neither `apply_graphql_hierarchy` nor `build_issue_forest` consumes those nodes. The forest is built from each fetched issue's parent. `sub_issues_summary` is returned by the backend but has no frontend consumer in this checkout. Remove unnecessary selection from the board projection after recording the current UI contract. The mutation-oriented `PARENT_ONLY_GRAPHQL` also selects unused child numbers.

Keep parent title/milestone information for parents outside the loaded open set, both dependency directions, closing PR references including closed PRs, and the existing forest cycle protection. Preserve flat PR rows and the synthetic milestone `0` meaning no milestone. Do not use only visible UI descendants when preparing server-side cascades.

A later GraphQL-only board loader is possible, but it is a larger migration: the UI consumes raw Markdown, rendered HTML, author/avatar information, issue type/color, labels, assignees, comment counts, milestone information, dates, URLs, and issue/PR distinctions. Direct milestone issue and PR connections would each need their own cursor, and the no-milestone bucket needs a separate strategy. The hybrid approach captures most request-count savings without introducing all of that mapping at once. Prefer direct connections or the existing REST list over introducing search-index dependence into Planning.

**2. SDLC: separate collection from per-window calculation**

Evidence: `sdlc_service.py:69`, `sdlc_service.py:136`, `sdlc_metrics.py:562`, `sdlc_metrics.py:623`.

`compute_sdlc_delivery_series` calls the complete single-window collector once per week. Each call queries PRs merged or created since the start of that week, without an upper search bound, and only then filters to the week's exact timestamps. Older slices repeatedly download newer data. With fairly uniform activity, fetched PR rows grow roughly with `W(W+1)/2` rather than `W`.

After filtering opened PRs into a slice, the code makes one REST request per PR for reviews. The same PR is generally not reviewed again in every slice, because creation windows are disjoint; the repeated work is primarily the searches and returned PR rows. The REST review call uses `get`, not `get_paged`, so it also misses subsequent review pages.

Recommended delivery flow:

1. Capture one `as_of` and derive the complete interval and all weekly boundaries.
2. Fetch merged PRs over that whole bounded interval once.
3. Fetch PRs created over that whole interval once, with review submission times and review authors in the GraphQL projection.
4. Finish any review and label pagination, normalize/deduplicate PRs, then calculate every slice locally.

The GraphQL PullRequest schema exposes a reviews connection, allowing this combination. Fetch all pages needed to determine the first human submission; `reviews(first:1)` is insufficient because the first review may be from a bot or lack a submitted timestamp. [GitHub PR schema](https://docs.github.com/en/graphql/reference/pulls#pullrequest).

For four weeks and 40 eligible opened PRs, assuming every original search fits one page, delivery alone currently requires **8 search calls + 40 review calls**. The proposed shape has **two paginated search connections carrying the needed review data**, whose first pages can be batched. This is not a promise of two HTTP calls for every repository: nested pagination, search partitioning, and query-size budgets still apply.

Keep `(start, end]` UTC boundaries, oldest-first slices, all throughput and median breakdowns, eligible/included review counts, and current PR-type precedence. Preserve the distinction between PR-author bot detection and review-author bot detection. The existing review metric uses reviews available now for PRs created in a past slice; it does not restrict review submission to that slice's end. Changing that would change the displayed metric.

**3. Share data across the three SDLC consumers, with narrower standalone loaders**

Evidence: `sdlc_service.py:217`, `sdlc_service.py:319`, `sdlc_service.py:378`, `sdlc_report_cli.py:82`.

Escaped-defect series already fetches once before partitioning, but it loads open and closed milestones separately, all escape-labeled issues, and all merged PRs for each selected milestone, regardless of the requested reporting interval. Backlog repeats two REST searches for every week, downloads full issue objects, then uses only timestamps for counting.

Introduce a dashboard orchestrator, for example `GET /sdlc/dashboard?weeks=…`, that supplies one anchor time and collects shared facts:

- Repository milestone catalog: one paginated `state=all` collection, divided locally into open and closed groups, with no synthetic Planning placeholder.
- Merged PR facts over the requested interval, including milestone, classification labels, author, and changed lines. Use these for both delivery and escaped-defect denominators; eliminate the per-target merged-PR searches for this combined workflow.
- Created PR facts with reviews for first-review metrics.
- Escape issues created within the overall interval, carrying milestone and creation time.
- Bug issues created and currently closed bug issues closed within the overall interval, carrying the relevant timestamps. Partition both sets locally rather than querying each week.

Keep the full semver milestone catalog: previous-release attribution depends on the immediately previous milestone globally, not just the displayed release rows. Preserve current milestone/label attribution, non-bot denominators, exclusion of unclassified PRs from the escape denominator, and `null` rates when the denominator is zero.

A standalone escape loader should use a slim projection without changed lines, reviews, or other delivery fields. A standalone status loader should likewise avoid delivery fields. Sharing one larger fetched dataset is useful inside the dashboard request; forcing every separate consumer through a universal large query is unnecessary.

Bug search can initially remain REST with whole-interval collection. A slim GraphQL query can subsequently reduce payload size and batch created/closed searches. Do not replace timestamp filtering with date-only `total_count` results: the UI uses rolling timestamp boundaries, not whole calendar days. Retain separate created and closed populations so an issue opened earlier but closed in the interval is counted.

The existing cumulative computation functions and the CLI are additional internal consumers. Adapt the CLI to the same dashboard orchestration where useful. Do not accidentally date-bound cumulative escaped-defect calculations while optimizing the weekly UI path.

**4. Project Status: reuse all open PRs and stop borrowing delivery projections**

Evidence: `status_report_service.py:184`, `status_report_service.py:217`, `status_report_service.py:235`, `status_report_service.py:245`, `sdlc_metrics.py:341`.

The all-open-PR attention query already returns the timestamps, state, draft flag, title, and URL used by both Recently Updated and Backlog. Derive those sections from that same collection, applying the existing predicates and sorting. This removes two logical searches and their duplicate rows: **six collections become four**.

Retain independent merged-in-window, created-PR, and created-issue collections. Created PRs cannot safely be reconstructed from current open PRs plus PRs merged in the reporting window: a PR created during a historical window may have merged after its end and still belongs to the current opened-PR section.

Use four explicit projections: merged summary, created PR summary, created issue summary, and open-PR attention. Status does not need additions, deletions, labels, milestones, or PR-author classification, currently inherited from the shared SDLC helpers. Keep review author identity for the second-approval suffix and clipboard output.

The four initial connections can share a GraphQL operation with independent cursors, followed only by unfinished connections. Start conservatively if the attention/reviews selection is expensive. For all-open PRs, a paginated `repository.pullRequests(states:[OPEN])` connection avoids the search result ceiling; retain search for selective historical windows. [GitHub repository PR connection](https://docs.github.com/en/graphql/reference/repos#repository).

Preserve current semantics: inclusive UTC calendar dates; bot-authored PRs included; opened PRs exclude currently CLOSED/unmerged PRs but include MERGED PRs; current open state for attention and backlog; drafts may need creator attention; approval records are counted, not unique approvers or branch-protection satisfaction. Do not substitute `reviewDecision` or latest-review-per-user data for the current approval heuristic.

In this checkout, New Issues Opened filters by creation date only and does **not** exclude issues closed during the interval. Preserve that baseline during optimization; behavior from another checkout must not silently enter this refactor. Apply must fetch again even when dates are unchanged (`ProjectStatusPanel.jsx:175`, `:215`).

**5. Focused REST operations and count queries**

Evidence: `api.py:109`, `api.py:784`, `api.py:1385`, `api.py:1402`.

Most non-search REST lists omit `per_page`, including milestone items, comments, milestones, labels, assignees, reactions, and sub-issues. Set an explicit endpoint-supported page size, usually 100, while retaining Link pagination. For example, 100 repository issues currently take four list calls and can take one. GitHub documents the issue-list default as 30 and maximum as 100. [REST issue listing](https://docs.github.com/en/rest/issues/issues#list-repository-issues).

For label addition, use `POST /repos/{owner}/{repo}/issues/{number}/labels`; for one-label removal, use the corresponding DELETE endpoint. These return the label collection and avoid GET plus replacement PATCH, reducing ordinary changes from two calls to one while avoiding overwriting unrelated concurrent label edits. Update the frontend to consume a label result if useful; it currently ignores the full returned issue. Preserve success for already-present additions and deliberate handling of already-absent removals; distinguish a missing label from a missing/inaccessible issue when handling 404. [REST label operations](https://docs.github.com/en/rest/issues/labels#add-labels-to-an-issue).

For milestone close counts, query the milestone's `issues(states:[OPEN]) { totalCount }` and `pullRequests(states:[OPEN]) { totalCount }` together, using a minimal connection page size if required. No item bodies are needed. The schema exposes separate state-filtered connections, so the existing two-number warning can be retained. Fetch fresh counts when opening the confirmation. [GitHub milestone schema](https://docs.github.com/en/graphql/reference/issues#milestone).

Single-field issue edits, milestone CRUD, assignee replacement/removal, issue/comment creation, and Markdown preview are already direct REST operations. Keep them unless a measured combined workflow justifies a change. GraphQL mutation batching would still need authorization/identity validation, sequencing, and partial-failure handling; it is not transactional.

**6. Frontend orchestration, reactions, and caching**

Evidence: `MilestoneCard.jsx:183`, `IssueCard.jsx:337`, `CommentCard.jsx:34`, `Reactions.jsx:29`, `MarkdownInputModal.jsx:82`, `App.jsx:387`, `frontend/src/utils/*Cache.js`.

Sort changes are presentation-only: all required labels and issue numbers are already loaded. Apply the existing first-matching-label bucket order, numeric ordering, and recursive sibling sorting locally, or sort a backend-cached raw dataset. Expected GitHub requests for changing sort: **zero**, while explicit Refresh still reloads authoritative data.

Reaction effects in IssueCard and CommentCard use an empty result and `!reactionsLoading` as the trigger. On failure, loading becomes false while the result remains empty, triggering another request. A successful empty response with a stale nonzero summary does the same. Add explicit idle/loading/success/error state, cache valid empty results, and retry through a bounded policy or explicit refresh.

Issue reactions are rendered inside the expanded description, but fetched when the row mounts. Fetch when the description opens, or include them in a focused detail request. For comments, fetch paginated bodies and reactions together in GraphQL, or batch reaction enrichment for the REST comment page. Keep comments lazy. The GraphQL schema supports both raw/rendered comment bodies and reaction connections. [GitHub comment schema](https://docs.github.com/en/graphql/reference/issues#issuecomment).

Reactions must retain every displayed user's login and the existing Unknown fallback, as well as counts and emoji mapping. Counts alone cannot populate current tooltips. Paginate nested reactions; do not silently replace REST's complete list with `first:100`. Map GraphQL reaction enums to the existing display semantics.

Centralize metadata caching with explicit loaded state, in-flight deduplication, and keys that include repository and milestone state. Empty lists are valid cached results. Closed milestone lists are currently cached separately in each IssueCard; share them. MarkdownInputModal bypasses the shared in-flight promises when labels/assignees are empty. Manage dialogs revalidate in the background, while tab unmounts discard SDLC and Planning component state. Preserve necessary revalidation but coalesce duplicate requests.

Use small, documented freshness windows or conditional revalidation for metadata. Key backend caches by repository and authorization scope; invalidate relevant entries after writes, and ensure explicit refresh/Apply can obtain fresh data. Avoid caching reports only by dates indefinitely: their current PR state, labels, milestones, and review data can change. Persisted queries should not allow an earlier response to overwrite a newer selection. Request IDs and AbortController can prevent stale UI updates; browser cancellation alone does not guarantee already-running synchronous GitHub work stops.

REST ETag/Last-Modified revalidation can reduce transferred bytes; authenticated 304 responses do not consume the primary REST rate limit. Store the representation and pagination metadata, and handle 304 before JSON decoding. This still makes a network round trip. [GitHub REST best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api#use-conditional-requests).

Retain GitHub Markdown rendering for fidelity. Cache identical preview text/rendering mode and avoid re-rendering unchanged text on repeated Preview visits. If descriptions are split from row summaries later, preserve raw Markdown for editing and rendered HTML for display; this is a secondary payload optimization after eliminating request fan-out.

**7. Transport and hierarchy mutations**

Evidence: `api.py:56`, `api.py:83`, `api.py:242`, `sdlc_api.py:24`, `status_report_api.py:27`, `api.py:850`, `api.py:913`.

All GitHub-backed routes are async functions that directly call synchronous `requests` methods; retry backoff uses `time.sleep`. Those calls block the event loop in the serving worker. Browser `Promise.all` does not make those services concurrently awaitable. The supplied CLI starts one Uvicorn application without a multiworker configuration.

An incremental correction is synchronous route/dependency execution in FastAPI's threadpool, or explicit offloading of the complete blocking operation. Longer term, an async HTTP transport owned by application lifespan provides connection reuse and cancellation-aware waits. Changing only a helper to `def` does not offload it when an async route calls it directly. [FastAPI execution model](https://fastapi.tiangolo.com/async/#path-operation-functions).

Connector creates a Session for each backend request, has no explicit network timeout, and does not close the session despite the dependency docstring. Add deterministic cleanup, connection/read timeouts, and operation-level metrics. A lifespan-managed async client is a clean reuse option; do not share an unsynchronized mutable requests Session between worker threads. The existing `test_connection_closes_on_exit` only asserts header initialization, so add an actual cleanup assertion when implementing this change.

Reducing requests should precede increasing concurrency. Use a GitHub-aware queue/limiter, respect Retry-After and rate-limit reset headers, and bound read retries. GitHub recommends serial requests to reduce secondary throttling. Treat GraphQL queries sent by POST as reads for retry policy, but do not blindly retry content-creating mutations after an ambiguous timeout. The existing 504 retry wrapper applies to all verbs, including comment creation. [GitHub rate-limit handling guidance](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api#handle-rate-limit-errors-appropriately).

For reparenting, retain the descendant collection used for the cycle check and reuse it for milestone cascading. With `D` descendants and one child-list page per visited issue, a cross-milestone reparent currently uses `2(D+1)` child-list calls, two identity reads, one link write, and `D+1` milestone writes: `3D+6` requests. Reusing the traversal removes `D+1` reads before considering batching.

Batch child/parent identity reads, and batch traversal frontiers if further savings justify it. Include database/node IDs and relevant milestones in the projection. Clear-parent and adopt-parent currently fetch overlapping REST and GraphQL identity data that can be combined. Dependency and closing-reference operations also perform paired identity reads that can share one GraphQL query. Server-side validation must remain authoritative.

Subtree traversal must cover all actual descendants, including closed issues and other milestones. `_list_sub_issue_numbers` currently converts every failure to an empty list, which can produce incomplete cascades; the refactor should make incomplete reads explicit rather than treating them as leaf nodes. Preserve accurate mutation results, rollback/reconciliation of optimistic UI state, and partial-failure reporting.

**Pagination and correctness gates**

The existing code has completeness gaps: review REST calls are unpaged; GraphQL labels stop at 30, attention reviews at 100, dependencies at 50, and closing PR references at 100. None of those nested selections exposes continuation information. The board also skips an issue entirely after an enrichment exception (`api.py:343`). These are risks to address or explicitly characterize, not behaviors to copy silently into larger batches.

GitHub search returns at most 1,000 results. Whole-interval collection must detect oversized searches and partition them into smaller date/time or other disjoint ranges, deduplicating by stable ID. Use direct repository connections where practical; if a partition still exceeds the cap, continue partitioning or report incomplete data explicitly. REST search helpers also ignore `incomplete_results`; do not interpret an incomplete response as a complete report. [GraphQL search ceiling](https://docs.github.com/en/graphql/reference/search#search).

Each aliased root and each nested connection needs its own cursor and completion state. Reject or clearly surface partial GraphQL errors; missing data must not become an empty successful report. Retry only affected read batches where safe. Batch size should account for nested connections and execution time. Fewer HTTP calls do not necessarily mean fewer GraphQL points: GitHub has connection-based costs, node limits, and timeouts. Record `rateLimit.cost`, rate-limit headers, bytes, calls, retries, and elapsed time per operation. [GraphQL resource limits](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api).

**Suggested service boundaries**

These are proposed module responsibilities, not required names or implemented files.

| Layer | Responsibility |
| --- | --- |
| `github_client` | Transport, connection lifecycle, deadlines, rate-aware scheduling, error normalization, REST/GraphQL pagination primitives, metrics |
| `repository_catalog` | Open/closed milestones, labels, allowed assignees; scoped caches and invalidation |
| `planning_reader` / `issue_commands` | Board summaries, batched relationships, lazy issue/comment details; validated writes and cascades |
| `report_queries` | Explicit minimal PR/issue/review projections; reusable pagination without implicit bot filtering |
| `sdlc_service` | Whole-interval collection plan plus pure per-window aggregation; shared dashboard context |
| `status_report_service` | Status-specific collection and section classification with its own bot/date/review semantics |
| Frontend query layer | Shared loaded/in-flight state, mutation reconciliation, refresh behavior, stale-response protection |

Extract Connector from `api.py` so services no longer depend on route implementation. Split query construction/collection out of `sdlc_metrics.py`, leaving classification and aggregation reusable and independent of GitHub. This enables shared transport without forcing status, delivery, and escape consumers to request each other's fields.

**Implementation sequence and acceptance**

1. Record baseline request counts and complete UI fixtures. Add transport timing/counts; correct blocking execution, session cleanup, timeouts, and reaction retry state. Set explicit REST page sizes and implement focused label mutations.
2. Batch Planning relationships, remove unused selections, calculate close counts directly, and make sorting local. Verify hierarchy and mutation behavior against existing UI tests.
3. Collect delivery and backlog over one interval; include paginated reviews. Add the dashboard orchestrator and reuse merged PR facts for escaped-defect metrics. Keep standalone projections narrow.
4. Reuse open PRs within Project Status, introduce its small projections, and batch independent connections. Preserve Apply refresh and clipboard details.
5. Consolidate metadata caches, improve lazy detail loading, and optimize hierarchy mutation reads based on observed frequency.

Use the existing tests in `backend/tests/test_api.py`, `test_issue_hierarchy.py`, `test_sdlc_api.py`, `test_sdlc_metrics.py`, `test_status_report_api.py`, and the corresponding frontend component suites as a starting point. Some fixtures assert the old request topology, so preserve behavioral expectations while updating mock shapes.

Add meaningful acceptance cases for multi-page outer and nested connections, more than 1,000 search matches, bot-only initial review pages, repeated approvals by one user, unknown mergeability, timestamp boundaries, no-milestone items, external/closed parents, closed descendants, reaction failures/empty successes, and partially failed batches. Compare normalized UI-visible data and rich/plain clipboard output, not legacy backend payloads alone.

For an agreed finite fixture, assert the expected request reductions: 100 issue enrichment reads become two batches; label changes need one ordinary write; sorting needs no GitHub calls; status needs four logical collections; SDLC should not re-download overlapping windows. A responsiveness test should hold a mocked GitHub operation pending while verifying a separate lightweight endpoint remains responsive. Live read-only measurements are still needed to choose batch sizes and quantify p50/p95 latency, bytes, and rate cost.

When implementation touches backend code, the required acceptance command is `cd backend && tox` (using the project's uv environment, e.g. `uv run tox`). For frontend source changes, run `cd frontend && npm run format && npm run format:check && npm test -- --run`. This investigation changes only this document; application tests were inspected but not executed, and proposed GraphQL operations were not exercised against the configured repository.
