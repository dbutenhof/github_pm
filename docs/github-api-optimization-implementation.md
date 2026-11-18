# GitHub API optimization implementation

Implemented in the `optimize` workspace against baseline `a49ea37`. The original analysis is in [github-api-optimization.md](github-api-optimization.md). UI views, editing controls, report sections, clipboard output, and their date/review/classification rules are retained. Changes are uncommitted.

## Collection and mutation changes

| Consumer | Implementation | Request-count evidence |
| --- | --- | --- |
| Planning board | REST pages of 100 retain raw Markdown and rendered HTML. GraphQL aliases enrich 50 issues at a time with parents, dependencies, and closing PRs. Unused subtree summaries are omitted. | A 100-issue, single-page fixture needs one REST list request plus two enrichment requests, versus four REST list pages plus 100 enrichments before. Additional relationship pages are fetched separately. |
| SDLC dashboard and HTML CLI | One `/sdlc/dashboard` response uses a common timestamp and whole-interval facts. Merged PRs are shared between delivery and release metrics; created PRs include human-review data. Created and closed bugs remain separate populations. | Five logical searches in two GraphQL operations, plus one `state=all` milestone catalog page, for the finite fixture at 1, 4, and 52 weeks. Larger real populations require more pages, not duplicate weekly collection. |
| Standalone SDLC APIs | Existing routes remain available with focused collection plans; escaped-defect collection omits delivery-only size fields and reviews. Cumulative calculations retain all historical data. | No REST review request per PR; no weekly repeated milestone catalog. |
| Project Status | Three slim historical searches share one GraphQL operation. A separate paginated repository open-PR collection supplies attention, recently updated, and backlog sections. | Six logical collections become four, with two initial HTTP requests. The open-PR connection avoids Search's 1,000-result limit. |
| Label edits | Targeted REST add/remove operations return authoritative labels to the edited row and its parent list. Labels containing spaces or slashes are encoded. | One ordinary write instead of GET plus replacement PATCH. An already-absent label removal checks issue existence before treating 404 as success. |
| Milestone close confirmation | One GraphQL query returns separate open issue and PR counts. | No downloading issue/PR bodies for counts. |
| Parent/dependency/closing-reference edits | Identity pairs share GraphQL reads. Hierarchy traversal batches breadth-first frontiers and reuses the descendants found during cycle validation. | No second traversal for cross-milestone reparenting; closed and cross-milestone descendants remain included. |
| Comments and reactions | Comments keep REST raw/rendered bodies; comments with reactions receive batched GraphQL reaction details, including every user's login and the existing Unknown fallback. Issue reactions load when the description opens. | Removes per-comment reaction requests and hidden issue-reaction reads. Empty responses and failures finish an attempt instead of causing render-driven retry loops. |
| Sorting | Recursive sibling and PR ordering happens in the browser. Authoritative label-write results update the sorting inputs. | Changing label priority makes zero requests. |

These are verified fixture counts and control-flow comparisons, not production latency measurements.

## Service boundaries and completeness

- `github_client.py` owns transport, lifecycle, conditional metadata caching, scheduling, timeouts, and metrics. API and CLI consumers use scoped sessions; services no longer import the transport from route implementation.
- `report_queries.py` owns consumer-specific projections and independent root/nested pagination. `sdlc_metrics.py` contains pure calculations. `planning_reader.py` owns batched Planning reads, and `repository_catalog.py` owns metadata collection.
- Searches exceeding 1,000 matches split into disjoint date/time intervals and deduplicate stable IDs. A single-second partition exceeding the cap raises an explicit error. Cumulative searches use the entire possible GitHub history for partitioning, rather than the dashboard's weekly bounds.
- Labels, reviews, relationships, sub-issues, and comment reactions follow their own continuation cursors. Missing pagination data, repeated cursors, partial GraphQL errors, and incomplete REST search results fail explicitly.
- A failed milestone cascade reports completed issue numbers and the failed issue. GitHub writes are not transactional; failed or ambiguous writes are not automatically replayed. Planning reloads affected columns after hierarchy errors and after adopting a parent's milestone.

## Transport and freshness policy

Blocking GitHub operations run in the ASGI worker threadpool. A regression test holds a blocking operation pending while a separate lightweight request completes. Sessions close on both success and failure.

Each transport operation has a five-minute budget, including queue waits, with connect/read timeouts capped at 5/45 seconds. Requests sharing a token serialize within the process, writes are spaced by at least one second, and read retries are bounded at five attempts. REST and GraphQL rate-limit signals respect Retry-After/reset information; long throttles fail visibly rather than holding the queue indefinitely. Mutation timeouts and 5xx responses are not replayed.

Per-operation logs record calls, response bytes, retries, aggregate request/queue time, GraphQL cost, 304 counts, and rate-limit headers. Conditional metadata representations retain their pagination links and are scoped by token hash, repository, URL, and representation headers. Writes invalidate them; older reads cannot repopulate an invalidated cache. The backend cache retains at most 256 entries.

The frontend query layer coalesces in-flight reads and scopes entries by repository. Metadata stays fresh for 30 seconds; Planning lists, reactions, comments, and dashboard results for 15 seconds; identical Markdown previews for five minutes. At most 256 completed entries are retained, while pending requests finish without eviction loops. Mutations invalidate before and after the attempt, including ambiguous failures. Superseded reads rejoin the current request instead of publishing old data. Project Status Apply always fetches again; explicit Refresh obtains fresh data, including loaded collapsed milestone cards. Unopened cards and comments remain lazy. Report and Planning request generations prevent obsolete responses from replacing newer selections.

The synchronous-session/threadpool approach was selected from the analysis's transport alternatives. Full GraphQL board replacement, lifespan-managed async transport, and splitting descriptions from summary payloads were optional alternatives, not additional changes required for the selected design. Raw and rendered Markdown remain available without changing editor behavior.

## Validation

- `cd backend && UV_CACHE_DIR=/tmp/optimize-uv-cache uv run tox`: all five environments pass; **169 tests**, **90.88% coverage**.
- `cd frontend && npm run format && npm run format:check && npm test -- --run`: **199 tests** pass.
- `cd frontend && npm run build`: production build passes.
- `git diff --check`: passes.

The tests cover hierarchy and external parents, closed descendants, partial cascades, one-call label edits, shared report facts, UTC timestamp boundaries, bot filtering, review identity and approval semantics, nested/outer pagination, oversized search splitting, validator reuse and invalidation, stale-response protection, local sorting, lazy reactions, preview caching, and event-loop responsiveness. Existing report-copy and editing tests remain green. Obsolete tests tied to per-issue/per-week request shapes were replaced with equivalent behavioral assertions and request-count checks.

No authenticated live GitHub benchmark or browser end-to-end run was performed. Production p50/p95 latency, rate cost, and batch-size tuning remain measurements to take from the new instrumentation. GitHub data can change during paginated collection; the API does not provide a transactional snapshot. The queue and caches are per process, so separate server workers do not share throttling state.

Generated-by: Codex
