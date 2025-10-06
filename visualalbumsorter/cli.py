#!/usr/bin/env python3
"""Command-line entry point for Visual Album Sorter (vasort)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .core import Config, EnhancedPhotoProcessor, ImageClassifier, load_config
from .utils import create_provider, parse_arguments, setup_cli_logging
from .utils.cli import apply_cli_overrides, handle_info_commands

logger = logging.getLogger(__name__)

DEPRECATION_MESSAGE = (
    "This command is deprecated and will be removed in the next release. "
    "Use 'vasort' instead."
)


def verify_integrity(config: Config) -> int:
    """Run repository integrity checks."""
    from scripts.verify_integrity import IntegrityChecker

    logger.info("Running integrity verification…")
    checker = IntegrityChecker()
    checker.config = config
    results = checker.run_all_checks()

    if results["summary"]["issues_count"] > 0:
        logger.error("Found %s issues", results["summary"]["issues_count"])
        return 1

    logger.info("No critical issues found")
    return 0


def show_status(config: Config) -> int:
    """Show resumable processing status."""
    logger.info("=" * 60)
    logger.info("PROCESSING STATUS")
    logger.info("=" * 60)

    state_path = config.get_state_path()
    if state_path.exists():
        state = json.loads(state_path.read_text())
        logger.info("\n📊 State Information:")
        logger.info("  Last index processed: %s", state.get("last_index", 0))
        logger.info("  Batches completed: %s", state.get("batch_processed", 0))
        logger.info("  Total matches: %s", len(state.get("matches", [])))
        logger.info("  Errors recorded: %s", state.get("errors", 0))
    else:
        logger.info("\n📊 No state file found (fresh start)")

    done_path = config.get_done_path()
    done_count = 0
    if done_path.exists():
        done_count = sum(1 for line in done_path.read_text().splitlines() if line.strip())
        logger.info("\n✅ Photos processed: %s", done_count)
    else:
        logger.info("\n✅ No photos processed yet")

    try:
        import osxphotos

        db = osxphotos.PhotosDB()
        total_photos = len(db.photos())

        if total_photos:
            remaining = max(total_photos - done_count, 0)
            progress = (done_count / total_photos) * 100
            logger.info("\n📚 Library Statistics:")
            logger.info("  Total photos: %s", total_photos)
            logger.info("  Processed: %s", done_count)
            logger.info("  Remaining: %s", remaining)
            logger.info("  Progress: %.1f%%", progress)
        else:
            logger.info("\n📚 Library contains no photos")
    except Exception:  # pragma: no cover - environment-specific
        logger.warning("\n⚠ Could not access Photos library")

    try:
        from photoscript import PhotosLibrary

        photos_lib = PhotosLibrary()
        album_name = config.album.name
        for album in photos_lib.albums:
            if album.name == album_name:
                logger.info("\n📁 Album '%s': %s photos", album_name, len(album.photos()))
                break
        else:
            logger.info("\n📁 Album '%s' not created yet", album_name)
    except Exception:  # pragma: no cover - environment-specific
        logger.warning("\n⚠ Could not check album status")

    logger.info("\n" + "=" * 60)
    return 0


def analyze_work(config: Config) -> int:
    """Perform a dry run to estimate remaining work."""
    logger.info("=" * 60)
    logger.info("WORK ANALYSIS")
    logger.info("=" * 60)

    try:
        import osxphotos

        processor = EnhancedPhotoProcessor(config, None, enable_diagnostics=False)
        db = osxphotos.PhotosDB()
        all_photos = db.photos()
        total_photos = len(all_photos)
        photos_to_process, already_processed = processor._analyze_work_needed(all_photos)

        logger.info("\n📊 Analysis Results:")
        logger.info("  Total photos in library: %s", total_photos)
        logger.info("  Already processed: %s", already_processed)
        logger.info("  Need processing: %s", len(photos_to_process))

        if photos_to_process:
            avg_time_per_photo = 2.0
            total_time = len(photos_to_process) * avg_time_per_photo
            hours = int(total_time // 3600)
            minutes = int((total_time % 3600) // 60)
            logger.info("\n⏱️  Time Estimate:")
            logger.info("  Estimated processing time: %sh %sm", hours, minutes)
            batch_size = config.processing.batch_size
            batches = (len(photos_to_process) + batch_size - 1) // batch_size
            logger.info("\n📦 Batch Information:")
            logger.info("  Batch size: %s", batch_size)
            logger.info("  Number of batches: %s", batches)
        else:
            logger.info("\n✅ All photos have been processed!")
        logger.info("\n" + "=" * 60)
        return 0
    except Exception as exc:  # pragma: no cover - environment-specific
        logger.error("Error analyzing work: %s", exc)
        return 1


def reset_state(config: Config) -> int:
    """Delete state and done files."""
    state_path = config.get_state_path()
    done_path = config.get_done_path()

    if state_path.exists():
        state_path.unlink()
        logger.info("Removed state file")

    if done_path.exists():
        done_path.unlink()
        logger.info("Removed done file")

    logger.info("Processing state reset")
    return 0


def _process_library(
    config: Config, classifier: ImageClassifier, diagnostics_enabled: bool
) -> int:
    processor = EnhancedPhotoProcessor(config, classifier, enable_diagnostics=diagnostics_enabled)
    processor.process_library()
    return 0


def main(argv: Optional[list[str]] = None, *, warn_deprecated: bool = False) -> int:
    """CLI entry point used by both console scripts and wrappers."""
    if warn_deprecated:
        print(DEPRECATION_MESSAGE, file=sys.stderr)

    args = parse_arguments(argv)
    setup_cli_logging(args.verbose, args.quiet)

    config = load_config(args.config)
    config = apply_cli_overrides(config, args)
    config.setup_logging()

    if handle_info_commands(args, config):
        return 0

    if args.verify:
        return verify_integrity(config)

    if args.status:
        return show_status(config)

    if args.analyze_work is not None:
        return analyze_work(config, prompt_override=args.analyze_work)

    if args.reset_state:
        return reset_state(config)

    provider = create_provider(config.provider.__dict__)
    classifier = ImageClassifier(provider, config.task.__dict__)
    return _process_library(config, classifier, diagnostics_enabled=args.diagnostics)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
