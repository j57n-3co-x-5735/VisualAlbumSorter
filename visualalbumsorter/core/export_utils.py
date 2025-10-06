"""Helpers for exporting Photos library assets in expected formats."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _convert_to_jpeg_with_sips(source: Path, dest: Path) -> bool:
    """Convert an image to JPEG using macOS `sips` tool."""
    try:
        completed = subprocess.run(
            ["/usr/bin/sips", "-s", "format", "jpeg", str(source), "--out", str(dest)],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        logger.error("`sips` tool not found; cannot convert %s to JPEG", source)
        return False

    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="ignore")
        logger.error("`sips` conversion failed for %s: %s", source, stderr.strip())
        return False

    return True


def export_heic_as_jpeg(
    photo,
    dest_dir: Path,
    filename: str,
    *,
    use_photos_export: bool = False,
) -> Optional[Path]:
    """Export a HEIC photo as JPEG, handling older osxphotos versions gracefully.

    Args:
        photo: ``osxphotos.PhotoInfo`` instance.
        dest_dir: Directory where the JPEG should be written.
        filename: Target filename for the JPEG (should end with ``.jpeg``).
        use_photos_export: Whether to delegate export to the Photos app.

    Returns:
        Path to the exported JPEG on success, otherwise ``None``.
    """

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    export_kwargs = {
        "filename": filename,
        "overwrite": True,
    }
    if use_photos_export:
        export_kwargs["use_photos_export"] = True

    # First, try native convert_to_jpeg support (present in newer osxphotos versions).
    try:
        exported = photo.export(
            str(dest_dir),
            convert_to_jpeg=True,
            **export_kwargs,
        )
        if exported:
            return Path(exported[0])
    except TypeError as err:
        if "convert_to_jpeg" not in str(err):
            raise
        logger.debug("convert_to_jpeg unsupported by current osxphotos; falling back to sips")
    except Exception as err:  # pragma: no cover - defensive logging
        logger.warning(
            "Photos export with convert_to_jpeg failed for %s: %s",
            getattr(photo, "original_filename", "<unknown>"),
            err,
        )

    # Fallback: export the HEIC and convert via sips.
    fallback_name = f"{Path(filename).stem}_source.heic"
    fallback_kwargs = {
        "filename": fallback_name,
        "overwrite": True,
    }
    if use_photos_export:
        fallback_kwargs["use_photos_export"] = True

    exported = photo.export(str(dest_dir), **fallback_kwargs)
    if not exported:
        logger.error(
            "Failed to export HEIC source for %s", getattr(photo, "original_filename", "<unknown>")
        )
        return None

    source_path = Path(exported[0])
    jpeg_path = dest_dir / filename

    try:
        if not _convert_to_jpeg_with_sips(source_path, jpeg_path):
            return None
        return jpeg_path
    finally:
        try:
            source_path.unlink(missing_ok=True)
        except OSError:
            logger.debug("Could not remove temporary source file %s", source_path)

