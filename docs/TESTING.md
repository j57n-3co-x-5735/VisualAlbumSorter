# Testing Guide

The project ships with three layers of automated tests plus helper scripts for ad-hoc validation.

## Quick commands

```bash
# Activate the virtualenv first
source .venv/bin/activate

# Run the full unit suite (fast, pure-python)
pytest tests/unit

# Run integration smoke tests
pytest tests/integration

# Opt-in performance batch test
pytest -m performance tests/performance

# All suites with coverage (unit + integration)
pytest tests/unit tests/integration --cov=visualalbumsorter --cov-report=term --cov-report=html
```

> The performance marker is excluded from default runs so CI can opt-in selectively.

## Test structure

| Path | Purpose |
|------|---------|
| `tests/unit/` | Dataclasses, factory logic, provider adapters, diagnostics, classifier |
| `tests/integration/` | CLI wiring smoke tests with stubbed providers |
| `tests/performance/` | Enhanced processor batching under load |
| `tests/TEST_COVERAGE_REVIEW.md` | Living document tracking coverage hot spots & future scenarios |

Deprecated/legacy test artefacts live under `BACKUP/tests/` for reference.

## Markers & options

- `@pytest.mark.performance` – opt-in heavy tests (disabled by default)
- `-k "pattern"` – filter by test name
- `-m "not performance"` – exclude heavy tests explicitly (default behaviour)

## Adding new tests

1. Prefer colocating tests with the existing structure (unit/integration/performance).
2. Mock external dependencies (`requests`, Photos APIs) rather than hitting real services.
3. Update `tests/TEST_COVERAGE_REVIEW.md` if the coverage focus shifts.
4. Keep fixtures lightweight—leverage `tmp_path` for file-system state.

## Helpful scripts

- `scripts/test_classification.py` – send a single image through the classifier stack using config-provided provider settings.
- `scripts/verify_integrity.py` – check state and done files against the Photos library before/after major runs.
- `run_tests.py` – a standalone unittest-based runner kept for constrained environments without `pytest`.

## Troubleshooting test failures

- **Provider availability** – unit tests patch `check_server`; if you see real HTTP requests, ensure your patch covers the correct object.
- **File permissions** – diagnostics tests create snapshots under `storage.temp_dir`; ensure `tmp_path` is used in new tests.
- **Coverage drops** – regenerate `htmlcov` with the coverage command above and update the coverage review document with findings.
