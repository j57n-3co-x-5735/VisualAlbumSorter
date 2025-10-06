# Visual Album Sorter (vasort)
Open-source, on-device album automation for Mac.

Visual Album Sorter (vasort) — a privacy-first CLI that uses local vision models (Ollama, LM Studio, MLX VLM) to sort photos into rule-based albums and keep them up to date. Diagnostics-first. Resumable. Configurable (regex, keywords, custom rules).

**What it does**
- **Sorts your Photos library** using local vision models and rule-driven prompts.
- **Keeps albums current** by analysing new images and adding matches automatically.
- **Captures diagnostics** so every run documents batches, matches, skips, and errors.
- **Resumes safely** with state/done tracking so you never reprocess the same shot twice.

**Why it’s different**
- **Privacy-first**: runs entirely on your Mac with your choice of local provider.
- **Diagnostics-first**: batch metrics, snapshots, and progress reporting (`--diagnostics`).
- **Resumable runs**: inspect or reset state at any time (`--status`, `--reset-state`).
- **Configurable rules**: combine prompts, regex, keywords, and custom filters.
- **Album automation**: keeps Photos.app albums up to date without manual triage.

## Quickstart
```bash
## Homebrew (example tap)
brew install yourtap/vasort
vasort --status
vasort --diagnostics
vasort --analyze-work "dogs frisbee beach"
vasort --reset-state --rules "regex:dog|canine"

## PyPI (optional)
pip install visualalbumsorter
vasort --help
```
(Replace the tap/PyPI instructions with the distribution channel you prefer.)

## Local vision providers
- Ollama
- LM Studio
- MLX VLM

### Image conversion requirements
- macOS `sips` command-line tool (ships with macOS) is used as a fallback when exporting HEIC photos. No extra install needed, but ensure `/usr/bin/sips` is available if you customise your environment.
- Provider validation defaults to 50 MB per image, and now supports optional dimension limits. Tune `provider.settings.max_image_size_mb` (size in MB) and `provider.settings.max_image_dimension_px` (0 to disable) for your workload.

### Album automation behavior
- Matches are added to the target Photos album when the in-memory buffer reaches `processing.album_update_frequency`, and any remaining matches are flushed at batch end.
- The processor re-resolves (or creates) the album on every add to avoid stale handles.
- PhotosScript supports both `album.add_photos(...)` and `album.add(...)`; the sorter uses either depending on the installed version.
- macOS Automation permission is required so Python can control Photos. If adds don’t show up, grant permission under System Settings → Privacy & Security → Automation (allow your terminal/python to control Photos), then re-run.
 - Shared Albums caveat: adds target regular albums. iCloud Shared Albums/Shared Library aren’t scriptable targets; use a normal album you own.

## CLI reference
| Command | Purpose |
|---------|---------|
| `vasort --diagnostics` | Enable batch metrics, snapshots, and detailed progress logs |
| `vasort --status` | Show resumable session state and counts of processed photos |
| `vasort --analyze-work` | Perform a dry run to estimate remaining work and batches |
| `vasort --reset-state` | Clear checkpoints and cached UUIDs before a fresh run |

All standard options (`--config`, `--provider`, `--debug`, etc.) remain available; run `vasort --help` for the full banner.

## Scripts
- `scripts/test_classification.py` – send a single image through your configuration to inspect raw model output and rule evaluation.
- `scripts/verify_integrity.py` – check state/done tracking against your Photos library before or after major runs.

## Documentation
- [`docs/QUICK_START.md`](docs/QUICK_START.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/TESTING.md`](docs/TESTING.md)
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)

## License
Visual Album Sorter is released under the MIT License. See [`LICENSE`](LICENSE).

## Disclaimer
“Photos” and “Mac” are properties of their respective owners. This project is independent and not affiliated with or endorsed by Apple.

## Credits
- [osxphotos](https://github.com/RhetTbull/osxphotos)
- [photoscript](https://github.com/RhetTbull/photoscript)
- Local vision providers: Ollama, LM Studio, MLX VLM
