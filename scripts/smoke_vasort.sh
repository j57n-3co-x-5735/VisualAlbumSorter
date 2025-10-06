#!/usr/bin/env bash
set -euo pipefail

COMMAND=${1:-vasort}

$COMMAND --help >/dev/null
$COMMAND --status >/dev/null 2>&1 || true
$COMMAND --diagnostics --config config/visualalbumsorter_config.json >/dev/null 2>&1 || true
$COMMAND --analyze-work --config config/visualalbumsorter_config.json "test prompt" >/dev/null 2>&1 || true
