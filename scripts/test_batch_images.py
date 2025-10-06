#!/usr/bin/env python3
"""Test multiple images to find which ones cause errors."""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import osxphotos
from visualalbumsorter.providers.lm_studio import LMStudioProvider
from visualalbumsorter.core.config import load_config
from visualalbumsorter.core.export_utils import export_heic_as_jpeg

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_batch(config_path: str, num_images: int = 100):
    """Test a batch of images to find problematic ones.

    Args:
        config_path: Path to config file
        num_images: Number of images to test
    """
    print("\n" + "="*60)
    print(f"TESTING BATCH OF {num_images} IMAGES")
    print("="*60)

    try:
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

        # Get photos from library
        photosdb = osxphotos.PhotosDB()
        photos = photosdb.photos(images=True)

        if not photos:
            print("✗ No photos found in library")
            return

        # Limit to requested number
        photos = photos[:num_images]
        print(f"Testing {len(photos)} photos from library\n")

        # Setup temp directory
        temp_dir = config.storage.temp_dir
        temp_dir.mkdir(exist_ok=True, parents=True)

        # Track results
        success_count = 0
        error_count = 0
        validation_failed = 0
        errors = []

        for i, photo in enumerate(photos, 1):
            try:
                print(f"[{i}/{len(photos)}] Processing: {photo.original_filename}...", end='', flush=True)

                # Export photo (convert HEIC via Photos or fallback conversion)
                if photo.original_filename and photo.original_filename.upper().endswith('.HEIC'):
                    image_path = export_heic_as_jpeg(
                        photo,
                        temp_dir,
                        f"test_{photo.uuid}.jpeg",
                        use_photos_export=True,
                    )
                else:
                    exported = photo.export(
                        str(temp_dir),
                        f"test_{photo.uuid}.jpg",
                        overwrite=True
                    )
                    image_path = Path(exported[0]) if exported else None

                if not image_path:
                    print(" ✗ Failed to export")
                    logger.warning(f"Failed to export {photo.original_filename}")
                    continue

                # Validate image
                is_valid, error_msg = provider.validate_image(image_path)
                if not is_valid:
                    validation_failed += 1
                    print(f" ⚠️  VALIDATION FAILED")
                    print(f"              Reason: {error_msg}")
                    errors.append({
                        'photo': photo.original_filename,
                        'uuid': photo.uuid,
                        'error': f"Validation: {error_msg}"
                    })
                    # Clean up
                    image_path.unlink(missing_ok=True)
                    continue

                # Try to classify
                result = provider.classify_image(
                    image_path,
                    config.task.prompt,
                    max_retries=1
                )

                if result:
                    success_count += 1
                    print(f" ✓")
                else:
                    error_count += 1
                    print(f" ✗ FAILED")
                    errors.append({
                        'photo': photo.original_filename,
                        'uuid': photo.uuid,
                        'error': 'Empty response from LM Studio'
                    })

                # Clean up
                image_path.unlink(missing_ok=True)

            except KeyboardInterrupt:
                print("\n\nStopped by user")
                break
            except Exception as e:
                error_count += 1
                print(f" ✗ EXCEPTION")
                print(f"              Error: {e}")
                errors.append({
                    'photo': photo.original_filename,
                    'uuid': photo.uuid,
                    'error': str(e)
                })

        # Print summary
        print("\n" + "="*60)
        print("BATCH TEST SUMMARY")
        print("="*60)
        print(f"Total tested:       {i}")
        print(f"Successful:         {success_count} ({success_count/i*100:.1f}%)")
        print(f"Validation failed:  {validation_failed} ({validation_failed/i*100:.1f}%)")
        print(f"Classification failed: {error_count} ({error_count/i*100:.1f}%)")
        print("="*60)

        if errors:
            print("\nFAILED IMAGES:")
            print("-"*60)
            for err in errors[:20]:  # Show first 20
                print(f"  {err['photo']}")
                print(f"    UUID: {err['uuid']}")
                print(f"    Error: {err['error']}")
                print()

            if len(errors) > 20:
                print(f"  ... and {len(errors) - 20} more errors")

            # Save errors to file
            error_file = Path("failed_images.txt")
            with open(error_file, 'w') as f:
                for err in errors:
                    f.write(f"{err['photo']}\n")
                    f.write(f"  UUID: {err['uuid']}\n")
                    f.write(f"  Error: {err['error']}\n\n")

            print(f"\nFull error list saved to: {error_file}")

    except Exception as e:
        print(f"✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run batch test."""
    if len(sys.argv) < 2:
        print("Usage: python test_batch_images.py <config_file> [num_images]")
        print("Example: python test_batch_images.py config/character_rules.json 100")
        sys.exit(1)

    config_path = sys.argv[1]
    num_images = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    test_batch(config_path, num_images)


if __name__ == "__main__":
    main()
