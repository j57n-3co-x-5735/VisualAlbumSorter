# Visual Album Sorter Test Coverage Review

## Current Coverage Snapshot
- Overall coverage: **26.5%** (`htmlcov/index.html`) with 356 of 1,343 lines executed. *(Re-run coverage after refactor for current numbers.)*
- Lowest covered modules:
  - `visualalbumsorter/utils/cli.py` – CLI surface now branded around `vasort`; add dedicated tests.
  - `visualalbumsorter/core/photo_processor.py` – legacy processor still shipped but largely untested.
  - `visualalbumsorter/core/classifier.py` – rule evaluation paths mostly unverified.
  - Provider adapters (`visualalbumsorter/providers/*.py`) – retry/error paths need mocks.
- Mid coverage but still gap-prone:
  - `visualalbumsorter/core/photo_processor_enhanced.py` – core workflow logic mostly uncovered.
  - `visualalbumsorter/utils/provider_factory.py` – server availability checks only partly exercised.
  - `visualalbumsorter/utils/diagnostics.py` – lifecycle completion/reporting paths missing assertions.

## Execution Notes
- Prefer running `vasort --diagnostics` in a sandboxed library before touching real data.
- `run_tests.py` remains for environments without pytest, but standard developers should use `pytest`.

## High-Risk Untested Code Paths
- **Library orchestration:** `visualalbumsorter.core.photo_processor_enhanced` branches around empty workloads, diagnostics start/stop, and error recovery.
- **Stateful batching:** `_process_photos` handles batching, skip reasons, debug limits, album updates, and state persistence.
- **Diagnostics lifecycle:** `DiagnosticsTracker.complete_processing` and `_generate_final_report` can regress silently without assertions.
- **Provider factory guard rails:** `create_provider` immediately calls `provider.check_server()`; ensure failure paths stay covered.
- **CLI orchestration:** `visualalbumsorter.cli:main` handles all flags (`--diagnostics`, `--status`, `--analyze-work`, `--reset-state`); expand integration tests accordingly.

## Recommendations
1. **Stabilise CLI coverage**
   - Add integration tests with `vasort` invoking diagnostics/status/analyze/reset flows via `visualalbumsorter.cli.main`.
2. **Expand diagnostics coverage**
   - Exercise snapshot writing, final reports, and error summaries with deterministic fixtures.
3. **Provider robustness**
   - Mock `requests` retries/timeouts for each provider and assert payload correctness.
4. **Processor scenarios**
   - Use synthetic `osxphotos`/`photoscript` doubles to test resume logic, album updates, and skip reasons.

## Existing Test Documentation
- Planning documents remain under `tests/planning/` for scenario inventories.

Update this file as coverage improves.
