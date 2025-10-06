"""Command-line interface utilities for Visual Album Sorter."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from .provider_factory import create_provider, list_available_providers

if TYPE_CHECKING:  # pragma: no cover
    from ..core import Config

logger = logging.getLogger(__name__)

HELP_BANNER = """Visual Album Sorter (vasort)
Open-source, on-device album automation for Mac

Commands:
  --diagnostics      Print batch metrics and snapshots
  --status           Show resumable session state/done
  --analyze-work     Dry-run classification & rules
  --reset-state      Clear checkpoints and cache

Providers: Ollama | LM Studio | MLX VLM
"""

EXAMPLES = """Examples:
  vasort --status
  vasort --diagnostics --config config/my_rules.json
  vasort --analyze-work "golden retriever beach"
  vasort --reset-state --rules "regex:dog|canine"
  vasort --provider lm_studio --config config/my_rules.json
"""


def parse_arguments(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="vasort",
        description=HELP_BANNER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXAMPLES,
    )

    # Configuration
    parser.add_argument("--config", "-c", type=Path, help="Path to configuration file (JSON)")

    # Provider override
    parser.add_argument(
        "--provider",
        "-p",
        choices=["ollama", "lm_studio", "mlx_vlm"],
        help="Override provider type from config",
    )

    # Diagnostics & processing modifiers
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Enable comprehensive diagnostics during processing",
    )
    parser.add_argument("--debug", "-d", action="store_true", help="Run in debug mode (process limited photos)")
    parser.add_argument(
        "--debug-limit",
        type=int,
        default=1,
        help="Number of matches before stopping in debug mode (default: 1)",
    )
    parser.add_argument("--batch-size", type=int, help="Override batch size from config")

    # Session helpers
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show detailed processing status",
    )
    parser.add_argument(
        "--analyze-work",
        nargs="?",
        const="",
        metavar="PROMPT",
        help="Analyze how much work needs to be done without processing",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Reset processing state and start fresh",
    )

    # Rule overrides
    parser.add_argument(
        "--rules",
        type=str,
        help="Override classification rules for this run (e.g. 'regex:dog|canine' or 'keyword:dog,canine')",
    )

    # Album options
    parser.add_argument("--album-name", help="Override album name from config")
    parser.add_argument("--no-album", action="store_true", help="Do not add photos to album (dry run)")

    # Logging
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose (DEBUG) logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output (WARNING and above only)")
    parser.add_argument("--log-file", type=Path, help="Override log file path")

    # Info commands
    parser.add_argument("--list-providers", action="store_true", help="List available provider types and exit")
    parser.add_argument(
        "--check-server",
        action="store_true",
        help="Check if configured provider server is running and exit",
    )
    parser.add_argument("--show-config", action="store_true", help="Display current configuration and exit")

    # Diagnostic helpers
    parser.add_argument("--verify", action="store_true", help="Verify integrity of state and data")

    return parser.parse_args(argv)


def setup_cli_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Setup console logging based on CLI flags."""
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not verbose:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)


def apply_cli_overrides(config: Config, args: argparse.Namespace) -> Config:
    """Apply CLI argument overrides to configuration."""
    if args.provider:
        logger.info("Overriding provider type to: %s", args.provider)
        config.provider.type = args.provider

    if args.debug:
        logger.info("Debug mode enabled")
        config.processing.debug_mode = True
        config.processing.debug_limit = args.debug_limit

    if args.batch_size:
        logger.info("Overriding batch size to: %s", args.batch_size)
        config.processing.batch_size = args.batch_size

    if args.album_name:
        logger.info("Overriding album name to: %s", args.album_name)
        config.album.name = args.album_name

    if args.no_album:
        logger.info("Album updates disabled (dry run)")
        config.album.create_if_missing = False

    if args.analyze_work not in (None, ""):
        logger.info("Using CLI prompt override for analyse-work: %s", args.analyze_work)
        config.task.prompt = args.analyze_work

    if args.rules:
        logger.info("Applying CLI rule override: %s", args.rules)
        config.task.classification_rules = _parse_rules_arg(args.rules)

    if args.log_file:
        config.storage.log_file = str(args.log_file)

    if args.verbose:
        config.logging_config.level = "DEBUG"
    elif args.quiet:
        config.logging_config.level = "WARNING"

    return config


def handle_info_commands(args: argparse.Namespace, config: Optional[Config] = None) -> bool:
    """Handle informational commands that short-circuit normal execution."""
    if args.list_providers:
        providers = list_available_providers()
        print("\nAvailable provider types:")
        for name, description in providers.items():
            print(f"  - {name}: {description}")
        print()
        return True

    if args.show_config and config:
        print("\nCurrent configuration:")
        print(json.dumps(config.to_dict(), indent=2))
        print()
        return True

    if args.check_server and config:
        try:
            provider = create_provider(config.provider.__dict__)
            info = provider.get_info()
            status = "Available" if info.get("available") else "Unavailable"
            print(f"\nProvider: {info.get('provider')}")
            print(f"Model: {info.get('model')}")
            print(f"API URL: {info.get('api_url')}")
            print(f"Status: {status}")
            print()
        except Exception as exc:  # pragma: no cover - diagnostic path
            print(f"\nError checking provider: {exc}")
            print()
        return True

    return False


def _parse_rules_arg(value: str) -> dict:
    value = value.strip()
    lower = value.lower()

    if lower.startswith("regex:"):
        pattern = value.split(":", 1)[1].strip() or ".*"
        return {
            "type": "regex_match",
            "rules": [
                {
                    "name": "cli_regex",
                    "pattern": pattern,
                    "field": "normalized_response",
                }
            ],
            "match_all": True,
        }

    if lower.startswith("keyword:"):
        keywords = [kw.strip() for kw in value.split(":", 1)[1].split(",") if kw.strip()]
        return {
            "type": "keyword_match",
            "keywords": keywords or ["keyword"],
            "match_all": False,
        }

    if lower in {"always_yes", "yes"}:
        return {"type": "always_yes", "rules": [], "match_all": True}

    if lower in {"always_no", "no"}:
        return {"type": "always_no", "rules": [], "match_all": True}

    return {"type": "custom", "rules": [], "match_all": True}
