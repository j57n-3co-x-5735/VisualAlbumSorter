#!/usr/bin/env python3
"""Create placeholder test images with descriptive names."""

from PIL import Image
import os

# Define test images needed based on test cases
test_images = {
    # For classification tests - character features
    "blonde_hair_with_fox_ears.jpg": "Character with blonde/yellow hair AND fox ears",
    "yellow_hair_with_fox_ears_and_tail.jpg": "Character with yellow hair AND fox ears AND fox tail", 
    "black_hair_no_fox_features.jpg": "Character with black hair, NO fox features",
    "blonde_hair_no_fox_ears.jpg": "Character with blonde hair but NO fox ears",
    "fox_ears_but_black_hair.jpg": "Character with fox ears but black/dark hair",
    
    # For regex pattern matching tests
    "yellow_fox_complete.jpg": "Character with 'yellow' hair and 'fox' features clearly visible",
    "yellowish_not_yellow.jpg": "Character with 'yellowish' hair (not exact 'yellow' match)",
    "fox_like_features.jpg": "Character with 'fox-like' or 'foxlike' features",
    
    # For multiline response tests
    "complex_character_multiple_features.jpg": "Character with many features for detailed description",
    
    # For different image sizes
    "small_100x100.jpg": "Small 100x100 pixel image with character",
    "medium_4000x4000.jpg": "Medium 4000x4000 pixel image with character",
    "large_8000x8000.jpg": "Large 8000x8000 pixel image with character",
    
    # For edge cases
    "empty_white_image.jpg": "Blank white image with no content",
    "corrupted_partial.jpg": "Partially corrupted/incomplete JPEG (create manually)",
    "very_dark_image.jpg": "Very dark/low contrast image hard to analyze",
    
    # For general API testing
    "generic_test_photo.jpg": "Any generic photo for API timeout/retry tests",
    "test_character_1.jpg": "Test character image 1",
    "test_character_2.jpg": "Test character image 2",
    
    # For Reference-specific tests (based on config)
    "reference_character_match.jpg": "Reference character (yellow/blonde hair + fox ears/tail)",
    "reference_character_nonmatch.jpg": "Non-Reference character (different features)",
    
    # For album management tests
    "photo_001.jpg": "Photo for batch processing test 1",
    "photo_002.jpg": "Photo for batch processing test 2",
    "photo_003.jpg": "Photo for batch processing test 3",
}

# Create minimal placeholder images
for filename, description in test_images.items():
    # Determine size from filename
    if "100x100" in filename:
        size = (100, 100)
    elif "4000x4000" in filename:
        size = (4000, 4000)
    elif "8000x8000" in filename:
        size = (8000, 8000)
    else:
        size = (800, 600)  # Default size
    
    # Create image with description text
    img = Image.new('RGB', size, color='lightgray')
    
    # Save with minimal quality to keep file size small
    img.save(filename, 'JPEG', quality=1)
    print(f"Created: {filename} ({size[0]}x{size[1]})")

print(f"\nCreated {len(test_images)} placeholder images")
print("\nNOTE: Replace these with actual images matching the descriptions!")
