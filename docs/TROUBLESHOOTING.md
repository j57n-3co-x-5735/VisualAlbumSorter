# Troubleshooting Guide

This guide helps diagnose and fix common issues with Visual Album Sorter. For setup instructions see [docs/QUICK_START.md](QUICK_START.md).

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Common Issues](#common-issues)
3. [Understanding the "Early Completion" Problem](#understanding-the-early-completion-problem)
4. [Diagnostic Tools](#diagnostic-tools)
5. [State Management](#state-management)
6. [Performance Issues](#performance-issues)
7. [Provider-Specific Issues](#provider-specific-issues)

## Quick Diagnostics

Run these commands first to understand your current state:

```bash
# Check current processing status
vasort --status

# Verify integrity of state files
vasort --verify

# Analyze work needed without processing
vasort --analyze-work

# Run with full diagnostics
vasort --config config/your_config.json --diagnostics
```

## Common Issues

### Issue: "Processing appears to complete instantly"

**Symptoms:**
- Processing finishes immediately
- No photos are processed
- No clear indication of what happened

**Diagnosis:**
```bash
# Check if all photos are already processed
vasort --analyze-work

# Check state files
python scripts/verify_integrity.py --config config/your_config.json
```

**Solutions:**

1. **All photos already processed:**
   - The enhanced version now clearly reports: "NO NEW PHOTOS TO PROCESS"
   - Shows total photos and how many were previously processed
   - This is normal behavior when resuming a completed task

2. **Corrupted state:**
   ```bash
   # Reset state and start fresh
   vasort --reset-state
   ```

3. **Want to reprocess everything:**
   ```bash
   # Remove state files and start over
   rm ~/Pictures/YourTempDir/state.json
   rm ~/Pictures/YourTempDir/done.txt
   ```

### Issue: "Photos not being added to album"

**Diagnosis:**
```bash
# Check album status
vasort --status
```

**Solutions:**

1. **Album doesn't exist:**
   - Ensure `create_if_missing: true` in config
   - Check Photos.app permissions

2. **Mismatch between matches and album:**
   ```bash
   # Verify integrity
   python scripts/verify_integrity.py
   ```

3. **Photos.app sync issues:**
   - Restart Photos.app
   - Wait for iCloud sync to complete

4. **Diagnose add path:**
   - Set `"album_update_frequency": 1` temporarily and re-run.
   - Look for `Adding X photos to album` followed by `Successfully added X photos to album` in logs.
   - If you see a stack trace, grant Automation permission (System Settings → Privacy & Security → Automation) and retry.

### Shared albums and iCloud behaviour

- PhotosScript controls regular (local/iCloud) albums. It does not add to iCloud “Shared Albums” or “Shared Library” collections via scripting.
- If you target a shared album by name, adds may appear to succeed in logs but not be reflected in the UI. Prefer a normal album you own.
- iCloud sync can delay visibility across devices; if you just created/renamed albums, allow a few minutes or restart Photos.app.

### Issue: "Invalid image file" after exporting HEIC assets

**Symptoms:**
- Validation fails right after an export (`Invalid image file: cannot identify image file ...`)
- Logs show HEIC sources even though export requested JPEG

**Solutions:**

1. The sorter now falls back to macOS `sips` when `osxphotos` lacks native `convert_to_jpeg` support. Confirm `/usr/bin/sips` exists (default on macOS).
2. If you removed command-line tools, reinstall them with `xcode-select --install` to restore `sips`.
3. File and dimension validation are configurable: set `provider.settings.max_image_size_mb` (MB) or `provider.settings.max_image_dimension_px` (pixels, `0` disables) to suit your library.
4. Re-run `python3 scripts/test_heic_fix.py config/your_rules.json` to verify HEIC conversions validate successfully.

### Issue: "Processing seems stuck"

**Diagnosis:**
```bash
# Run with diagnostics to see detailed progress
vasort --diagnostics --verbose
```

**Solutions:**

1. **Provider not responding:**
   ```bash
   # Check provider status
   vasort --check-server
   ```

2. **Large photo causing timeout:**
   - Check diagnostic logs for timeout errors
   - Increase timeout in config

3. **Memory issues:**
   - Reduce batch_size in config
   - Monitor memory usage during processing

## Understanding the "Early Completion" Problem

The original issue where processing appears to end early is actually a **reporting problem**, not a processing problem. Here's what happens:

### The Real Sequence of Events

1. **First Run:**
   - Processes all photos
   - Saves progress to state.json and done.txt
   - Reports completion correctly

2. **Subsequent Runs:**
   - Loads previous state
   - Checks which photos are already done
   - Finds no new photos to process
   - **OLD BEHAVIOR:** Exits quietly or with minimal message
   - **NEW BEHAVIOR:** Clearly reports "NO NEW PHOTOS TO PROCESS" with statistics

### How the Enhanced Version Fixes This

The enhanced processor now:

1. **Analyzes work before starting:**
   ```
   Analyzing library to determine work needed...
   Analysis complete:
     - Total photos: 5,000
     - Already processed: 5,000
     - Need processing: 0
   ```

2. **Provides clear completion messages:**
   ```
   ========================================
   NO NEW PHOTOS TO PROCESS
   All 5,000 photos have already been processed
   ========================================
   ```

3. **Shows detailed progress during processing:**
   ```
   Progress: Session 45.0% (450/1000) | Overall 72.5% (3625/5000)
   ```

4. **Generates comprehensive final reports:**
   - Library status (total, processed, remaining)
   - Session results (processed, matched, errors, skipped)
   - Performance metrics (duration, photos/minute)
   - Completion percentage

## Diagnostic Tools

### 1. Status Command

Shows current state without processing:

```bash
vasort --status
```

Output includes:
- State file information
- Number of processed photos
- Library statistics
- Album status

### 2. Integrity Verification

Checks for inconsistencies:

```bash
python scripts/verify_integrity.py --config config/your_config.json
```

Checks:
- State file validity
- Done file integrity
- Orphaned temp files
- State/done consistency
- Photos library access
- Album state

### 3. Work Analysis

Preview what needs to be done:

```bash
vasort --analyze-work
```

Shows:
- Total photos in library
- Already processed count
- Photos needing processing
- Time estimate
- Batch information

### 4. Full Diagnostics Mode

Run with comprehensive tracking:

```bash
vasort --diagnostics
```

Features:
- Detailed progress logging every 10 photos
- Processing time tracking
- Error categorization
- Skip reason tracking
- Diagnostic log file in temp directory

### 5. Test Single Image

Test classification without full processing:

```bash
python scripts/test_classification.py ~/Pictures/test.jpg --config config/your_config.json --verbose
```

## State Management

### Understanding State Files

**state.json:**
```json
{
  "last_index": 1500,        // Last processed photo index
  "matches": [...],           // UUIDs of matched photos
  "errors": 0,                // Error count
  "batch_processed": 15       // Number of batches completed
}
```

**done.txt:**
```
UUID-1234-5678-90AB
UUID-2345-6789-01BC
...
```
One UUID per line for each processed photo.

### Repair Commands

Fix common state issues:

```bash
# Remove duplicate entries
python scripts/verify_integrity.py --fix-duplicates

# Clean orphaned temp files
python scripts/verify_integrity.py --clean-temp

# Full repair (both above)
python scripts/verify_integrity.py --repair
```

## Performance Issues

### Slow Processing

1. **Check processing times:**
   ```bash
   vasort --diagnostics
   ```
   Look for "Average time per photo" in the final report.

2. **Optimize batch size:**
   ```json
   "processing": {
     "batch_size": 50  // Reduce if memory constrained
   }
   ```

3. **Check provider performance:**
   - Ensure model is loaded in memory
   - Check CPU/GPU usage
   - Consider switching providers

### Memory Issues

1. **Reduce batch size** in config
2. **Clean temp files** regularly:
   ```bash
   python scripts/verify_integrity.py --clean-temp
   ```
3. **Monitor with diagnostics:**
   ```bash
   vasort --diagnostics
   ```

## Provider-Specific Issues

### Ollama

```bash
# Check if running
curl http://127.0.0.1:11434/api/tags

# Restart
ollama serve

# Check model
ollama list
```

### LM Studio

```bash
# Check server
curl http://localhost:1234/v1/models

# Ensure model is loaded in UI
```

### MLX VLM

```bash
# Check server
curl http://127.0.0.1:8000

# Restart with specific model
mlx_vlm.server --model mlx-community/Phi-3-vision-128k-instruct-4bit
```

## Debug Workflow

When encountering issues, follow this workflow:

1. **Check Status:**
   ```bash
   vasort --status
   ```

2. **Verify Integrity:**
   ```bash
   python scripts/verify_integrity.py
   ```

3. **Analyze Work:**
   ```bash
   vasort --analyze-work
   ```

4. **Test Classification:**
   ```bash
   python scripts/test_classification.py [test_image]
   ```

5. **Run with Diagnostics:**
   ```bash
   vasort --diagnostics --verbose
   ```

6. **Check Diagnostic Logs:**
   ```bash
   ls -la ~/Pictures/YourTempDir/diagnostics/
   cat ~/Pictures/YourTempDir/diagnostics/diagnostic_*.json
   ```

## Getting Help

If issues persist after following this guide:

1. **Collect diagnostic information:**
   ```bash
   vasort --verify > diagnostics.txt
   vasort --status >> diagnostics.txt
   ```

2. **Check the diagnostic log:**
   - Located in `~/Pictures/YourTempDir/diagnostics/`
   - Contains detailed event tracking

3. **Report issue with:**
   - Diagnostic output
   - Configuration file (remove sensitive info)
   - Console output with `--verbose`
   - Diagnostic JSON file

## Summary

The enhanced photo sorter now provides:

- **Clear communication** about what's happening
- **Detailed progress tracking** during processing
- **Comprehensive diagnostics** for troubleshooting  
- **State verification** tools
- **Work analysis** without processing
- **Session summaries** showing exactly what was done

The "early completion" issue is resolved by clearly distinguishing between:
- Fresh start (no state)
- Resuming (partial completion)
- Already complete (no work needed)

Each scenario now has distinct, informative output to prevent confusion.
