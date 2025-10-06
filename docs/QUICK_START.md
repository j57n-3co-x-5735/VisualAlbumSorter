# Quick Start

This guide walks you through running Visual Album Sorter end-to-end with diagnostics and resumable state.

## 1. Prerequisites

- macOS with access to the Photos library
- Python 3.10+
- At least one local vision provider (Ollama, LM Studio, or MLX VLM)

## 2. Environment Setup

```bash
# Clone and enter the project
git clone <your-remote-url>
cd visualalbumsorter

# Create / reuse the virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
pip install -r requirements-test.txt  # optional: test tooling
```

## 3. Verify your provider (LM Studio example)

Start LM Studio with `qwen2.5-omni-3b` loaded, then confirm the OpenAI-compatible endpoint responds:

```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-omni-3b",
    "messages": [
      { "role": "system", "content": "Always answer in rhymes. Today is Thursday" },
      { "role": "user", "content": "What day is it today?" }
    ],
    "temperature": 0.7,
    "max_tokens": -1,
    "stream": false
}'
```

You should see a rhymed response, confirming the server is reachable.

## 4. Configure the sorter

Use the sample config as a starting point:

```bash
cp config/visualalbumsorter_config.json config/my_rules.json
# Edit config/my_rules.json to adjust rules, provider settings, temp paths, etc.
```

Key entry points:

- `vasort` – primary CLI with diagnostics, status, verification helpers
- `visualalbumsorter` – long-form alias that invokes the same entry point

## 5. Run the sorter

```bash
# Recommended: run with diagnostics enabled
vasort --config config/my_rules.json --diagnostics

# Check progress without processing
vasort --status --config config/my_rules.json

# Analyse outstanding work
vasort --analyze-work --config config/my_rules.json
```

Visual Album Sorter reports how many photos are pending, logs detailed diagnostics, and auto-creates albums if configured.

### Album automation & permissions
- The sorter adds matches to your configured Photos album in small batches governed by `processing.album_update_frequency`.
- It re-resolves (or creates) the album on every add; you don’t need to restart if an album was created mid-run.
- On first use, macOS may prompt for permission to control Photos. Grant it under System Settings → Privacy & Security → Automation, then re-run.
- For quick diagnosis set `"album_update_frequency": 1` and watch for log lines like `Adding 1 photos to album` and `Successfully added 1 photos to album`.

### Completion semantics
- The final banner shows `ALL PHOTOS COVERED - FINAL DIAGNOSTIC REPORT` when there are no items left to process or skip. Otherwise it shows `SESSION COMPLETE - REVIEW REQUIRED - FINAL DIAGNOSTIC REPORT` along with a "Photos remaining" count.
- Overall completion reflects library coverage, not just classification: it includes items processed this session plus items intentionally skipped (videos/GIFs if configured), in addition to any previously processed items.
- To finish remaining work, run `vasort --analyze-work --config ...` to see what’s left, or simply re-run with the same config to resume.

## 6. Resetting or starting fresh

```bash
# Reset cached state/done tracking
vasort --config config/my_rules.json --reset-state

# Manual reset (if you changed the storage.temp_dir path)
rm -f /path/to/temp_dir/state.json
rm -f /path/to/temp_dir/done.txt
# (replace /path/to/temp_dir with the value from your config)
```

> Tip: always run `--status` and `--analyze-work` before long sessions so you know exactly what will be processed.

## 7. Next steps

- Review [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) to understand the internals
- Follow [`docs/TESTING.md`](TESTING.md) to validate changes
- Check [`docs/TROUBLESHOOTING.md`](TROUBLESHOOTING.md) if anything looks off
