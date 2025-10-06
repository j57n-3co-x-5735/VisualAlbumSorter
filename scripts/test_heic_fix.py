#!/usr/bin/env python3
"""Test HEIC conversion fix."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import osxphotos
from visualalbumsorter.core.config import load_config
from visualalbumsorter.providers.lm_studio import LMStudioProvider
from visualalbumsorter.core.export_utils import export_heic_as_jpeg


def test_heic_photos(config_path: str):
    """Test HEIC photos specifically."""

    print("Testing HEIC photo conversion...")
    print("="*60)

    # Load config
    config = load_config(Path(config_path))

    # Create provider
    provider_settings = config.provider.settings
    provider_extra = {
        k: v for k, v in provider_settings.items()
        if k not in {"model", "api_url"}
    }
    provider = LMStudioProvider(
        model_name=provider_settings["model"],
        api_url=provider_settings["api_url"],
        config=provider_extra
    )

    # Get HEIC photos
    photosdb = osxphotos.PhotosDB()
    heic_photos = [p for p in photosdb.photos(images=True)
                   if p.original_filename and p.original_filename.upper().endswith('.HEIC')]

    if not heic_photos:
        print("No HEIC photos found in library")
        return

    print(f"Found {len(heic_photos)} HEIC photos")
    print("\nTesting first 5 HEIC photos:")
    print("-"*60)

    temp_dir = config.storage.temp_dir
    temp_dir.mkdir(exist_ok=True, parents=True)

    for i, photo in enumerate(heic_photos[:5], 1):
        print(f"\n{i}. {photo.original_filename}")

        try:
            # Test export with JPEG conversion using Photos app or fallback conversion
            image_path = export_heic_as_jpeg(
                photo,
                temp_dir,
                f"test_{photo.uuid}.jpeg",
                use_photos_export=True,
            )

            if image_path and image_path.exists():
                print(f"   ✓ Export successful: {image_path.name}")
                print(f"   File size: {image_path.stat().st_size / 1024:.1f} KB")

                # Validate
                is_valid, error_msg = provider.validate_image(image_path)
                if is_valid:
                    print(f"   ✓ Validation passed")

                    # Try classification
                    result = provider.classify_image(image_path, config.task.prompt, max_retries=1)
                    if result:
                        print(f"   ✓ Classification successful")
                        print(f"   Response: {result[:100]}...")
                    else:
                        print(f"   ✗ Classification failed")
                else:
                    print(f"   ✗ Validation failed: {error_msg}")

                # Clean up
                image_path.unlink(missing_ok=True)
            else:
                print(f"   ✗ Export failed")

        except Exception as e:
            print(f"   ✗ Error: {e}")

    print("\n" + "="*60)
    print("HEIC test complete")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_heic_fix.py <config_file>")
        sys.exit(1)

    test_heic_photos(sys.argv[1])
