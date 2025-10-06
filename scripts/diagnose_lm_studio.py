#!/usr/bin/env python3
"""Diagnose LM Studio issues by testing the server and model."""

import sys
import json
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from visualalbumsorter.providers.lm_studio import LMStudioProvider
from visualalbumsorter.core.config import load_config

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_lm_studio_server():
    """Check if LM Studio server is running and responding."""
    print("\n" + "="*60)
    print("CHECKING LM STUDIO SERVER")
    print("="*60)

    url = "http://localhost:1234/v1/models"

    try:
        resp = requests.get(url, timeout=5)
        print(f"✓ Server is running (status {resp.status_code})")

        if resp.status_code == 200:
            data = resp.json()
            models = data.get("data", [])
            print(f"\nAvailable models: {len(models)}")
            for model in models:
                print(f"  - {model.get('id', 'unknown')}")
            return True
        else:
            print(f"✗ Server returned status {resp.status_code}")
            print(f"Response: {resp.text[:200]}")
            return False

    except requests.ConnectionError:
        print("✗ Cannot connect to LM Studio server")
        print("  Make sure LM Studio is running on http://localhost:1234")
        return False
    except Exception as e:
        print(f"✗ Error checking server: {e}")
        return False


def test_simple_request():
    """Test a simple text-only request."""
    print("\n" + "="*60)
    print("TESTING SIMPLE TEXT REQUEST")
    print("="*60)

    url = "http://localhost:1234/v1/chat/completions"

    payload = {
        "model": "qwen2.5-omni-3b",
        "messages": [
            {
                "role": "user",
                "content": "Say hello in one word"
            }
        ],
        "max_tokens": 10
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        print(f"Status: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"✓ Text request successful")
            print(f"Response: {content}")
            return True
        else:
            print(f"✗ Request failed with status {resp.status_code}")
            try:
                error_data = resp.json()
                print(f"Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"Response: {resp.text[:200]}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_image_request(config_path: str):
    """Test an image request with actual image from Photos library."""
    print("\n" + "="*60)
    print("TESTING IMAGE REQUEST")
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

        # Get first photo from library to test
        import osxphotos
        photosdb = osxphotos.PhotosDB()
        photos = photosdb.photos(images=True)

        if not photos:
            print("✗ No photos found in library")
            return False

        test_photo = photos[0]
        print(f"Testing with photo: {test_photo.original_filename}")

        # Export photo to temp location
        temp_dir = Path.home() / "Pictures" / "VASorterTemp"
        temp_dir.mkdir(exist_ok=True)

        exported = test_photo.export(str(temp_dir), f"test_{test_photo.uuid}.jpg")
        if not exported:
            print("✗ Failed to export photo")
            return False

        image_path = Path(exported[0])
        print(f"Exported to: {image_path}")
        print(f"File size: {image_path.stat().st_size / 1024:.1f} KB")

        # Validate image
        is_valid, error_msg = provider.validate_image(image_path)
        if not is_valid:
            print(f"✗ Image validation failed: {error_msg}")
            return False
        else:
            print("✓ Image validation passed")

        # Try to classify
        print("\nSending classification request...")
        result = provider.classify_image(
            image_path,
            config.task.prompt,
            max_retries=1
        )

        if result:
            print(f"✓ Classification successful")
            print(f"Response: {result}")
            return True
        else:
            print(f"✗ Classification returned empty response")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run diagnostic tests."""
    if len(sys.argv) < 2:
        print("Usage: python diagnose_lm_studio.py <config_file>")
        print("Example: python diagnose_lm_studio.py config/character_rules.json")
        sys.exit(1)

    config_path = sys.argv[1]

    print("\n" + "="*60)
    print("LM STUDIO DIAGNOSTIC TOOL")
    print("="*60)

    # Run tests
    server_ok = check_lm_studio_server()
    if not server_ok:
        print("\n✗ LM Studio server is not accessible")
        print("Please start LM Studio and load a model before running tests")
        sys.exit(1)

    text_ok = test_simple_request()
    if not text_ok:
        print("\n✗ Basic text requests are failing")
        print("Check your LM Studio model configuration")
        sys.exit(1)

    image_ok = test_image_request(config_path)

    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    print(f"Server Check:  {'✓ PASS' if server_ok else '✗ FAIL'}")
    print(f"Text Request:  {'✓ PASS' if text_ok else '✗ FAIL'}")
    print(f"Image Request: {'✓ PASS' if image_ok else '✗ FAIL'}")
    print("="*60)

    if not image_ok:
        print("\nImage requests are failing. Common causes:")
        print("  1. Model doesn't support vision (need a vision model like qwen2.5-omni)")
        print("  2. Image format not supported by model")
        print("  3. Image size too large")
        print("  4. LM Studio configuration issue")
        sys.exit(1)
    else:
        print("\n✓ All tests passed! LM Studio is working correctly.")


if __name__ == "__main__":
    main()
