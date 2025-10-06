# Architecture Overview

This document summarises the moving parts of the Visual Album Sorter and how they interact at runtime.

## High-level flow

```
CLI (`visualalbumsorter.cli` / `vasort`)
        │
        ├── loads configuration (visualalbumsorter/core/config.py)
        ├── creates provider via factory (visualalbumsorter/utils/provider_factory.py)
        ├── instantiates ImageClassifier (visualalbumsorter/core/classifier.py)
        └── drives EnhancedPhotoProcessor
                     │
                     ├── scans Photos library via osxphotos
                     ├── exports media and delegates to ImageClassifier
                     ├── manages state + "done" UUID tracking
                     └── (enhanced) streams events into DiagnosticsTracker
```

## What makes it special
Visual Album Sorter isn’t just another batch script. It understands the reality of living with a huge Photos library: restarts happen, photo counts explode, and you still want confidence that nothing slipped through the cracks.

* **Native Photos intelligence** – it talks to Apple Photos directly, respects albums, and keeps a tidy record of every UUID it has already processed.
* **Narrated progress** – diagnostics snapshots tell you how far you are, what matched, what got skipped, and why, so surprises are rare.
* **Provider flexibility** – switch between Ollama, LM Studio, or MLX models without rewriting code; the factory handles the plumbing.
* **Fully local control** – your images stay on your Mac, and you decide which AI runs the classification work.

## Core packages

### `visualalbumsorter/core`
- **`config.py`** – dataclasses describing task, provider, processing, storage, logging configuration. Provides `load_config` helper and logging setup.
- **`classifier.py`** – normalises LLM responses and evaluates classification rules (`regex_match`, `keyword_match`, etc.).
- **`photo_processor.py`** – legacy processor with minimal diagnostics; retained for simpler use cases.
- **`photo_processor_enhanced.py`** – preferred processor. Adds batching metrics, album batching, done-UUID persistence, and hooks into the diagnostics subsystem.

#### Album update flow
- Matches for the current batch are buffered; when the buffer reaches `processing.album_update_frequency`, the processor resolves (or creates) the target album and adds the matching Photos items.
- Album adds are resilient to API differences across PhotosScript versions: `album.add_photos(...)` is preferred; `album.add(...)` is used as a fallback.
- At the end of a batch, any remaining buffered matches are flushed.

### `visualalbumsorter/providers`
- **`base.py`** – abstract base with helpers like `encode_image` and `check_server` contract.
- **`ollama.py`, `lm_studio.py`, `mlx_vlm.py`** – concrete adapters that format payloads, post to the provider, implement retry/backoff, and expose availability checks.

### `visualalbumsorter/utils`
- **`provider_factory.py`** – normalises provider configuration, instantiates the correct adapter, enforces availability before returning control to the CLI.
- **`diagnostics.py`** – `PhotoStats`, `ProcessingEvent`, and `DiagnosticsTracker` that capture end-to-end metrics, snapshots, and final reports.
- **`cli.py`** – argument parsing, logging setup, and command helpers consumed by both CLI entry points.

## CLI entry points

- **`vasort`** *(recommended)* – wraps the enhanced processor, exposes status/analyse/verify commands, and integrates the diagnostics tracker.
- **`BACKUP/legacy/photo_sorter_legacy.py`** – archived streamlined variant targeting the legacy processor for minimal setups.

Both expect a resolved `Config` instance and delegate provider creation to `create_provider`.

## State & storage layout

- **State file** (`storage.state_file`) – persists progress (`last_index`, `matches`, batch counters).
- **Done file** (`storage.done_file`) – newline-separated UUID list used to skip processed assets.
- **Diagnostics directory** (`<temp_dir>/diagnostics/`) – contains timestamped JSON snapshots when diagnostics are enabled.

## Testing layers

- **Unit (`tests/unit/`)** – covers config dataclasses, classifier logic, diagnostics tracker, provider factory, and provider adapters (using mocked HTTP).
- **Integration (`tests/integration/test_cli_end_to_end.py`)** – smoke-tests the enhanced CLI wiring with stubs to guarantee command-line flows don’t regress.
- **Performance (`tests/performance/test_enhanced_processor_performance.py`)** – stress-tests the enhanced processor’s batching loop with 500 mocked photos.

Markers allow selective execution: `pytest tests/unit`, `pytest tests/integration`, `pytest -m performance`.

## Supporting scripts

- **`scripts/test_classification.py`** – ad-hoc helper for single-image classification via configured providers.
- **`scripts/verify_integrity.py`** – checks persisted state against live Photos library metadata.
- **`scripts/manage_providers.py`** – templates for provider health checks.

## Design principles

- **Provider agnosticism** – all providers implement the same interface, so switching is configuration-only.
- **Resumable processing** – state files and done lists guarantee idempotent reruns.
- **Diagnostics-first** – the enhanced CLI and tracker favour clear reporting (progress logs, JSON snapshots).
- **Testable boundaries** – adapters, factory, diagnostics, and classifier are all designed for pure-unit coverage with mocks.
