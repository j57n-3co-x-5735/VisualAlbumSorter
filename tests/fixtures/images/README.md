# Test Images Guide

This directory contains placeholder images for testing the photo classification system. 
Please replace these minimal JPEG placeholders with actual images matching the descriptions below.

## Character Classification Images

### Core Positive Match Images
- **`blonde_hair_with_fox_ears.jpg`**
  - Should contain: Character with blonde/yellow hair AND fox ears
  - Expected result: Classification = "yes"
  
- **`yellow_hair_with_fox_ears_and_tail.jpg`**
  - Should contain: Character with yellow hair AND fox ears AND fox tail
  - Expected result: Classification = "yes" (all features present)

- **`reference_character_match.jpg`**
  - Should contain: Reference character or similar (blonde/yellow hair + fox ears/tail)
  - Expected result: Classification = "yes"

### Negative Match Images
- **`black_hair_no_fox_features.jpg`**
  - Should contain: Character with black/dark hair, NO fox features
  - Expected result: Classification = "no"

- **`blonde_hair_no_fox_ears.jpg`**
  - Should contain: Character with blonde hair but NO fox ears
  - Expected result: Classification = "no" (missing required feature)

- **`fox_ears_but_black_hair.jpg`**
  - Should contain: Character with fox ears but black/dark hair (not yellow/blonde)
  - Expected result: Classification = "no" (wrong hair color)

- **`reference_character_nonmatch.jpg`**
  - Should contain: Any character that doesn't match Reference features
  - Expected result: Classification = "no"

## Pattern Matching Test Images

### Exact Match Tests
- **`yellow_fox_complete.jpg`**
  - Should contain: Character with clear "yellow" hair and "fox" features
  - Tests: Exact word matching in response

- **`yellowish_not_yellow.jpg`**
  - Should contain: Character with "yellowish" or "yellow-ish" hair
  - Tests: Whether partial matches are handled correctly (should be "no" for exact match)

### Flexible Pattern Tests
- **`fox_like_features.jpg`**
  - Should contain: Character with "fox-like" or "foxlike" features
  - Tests: Hyphenated and compound word matching

- **`complex_character_multiple_features.jpg`**
  - Should contain: Character with many distinct features (hair, ears, tail, outfit, etc.)
  - Tests: Multi-line response parsing and multiple pattern matching

## Image Size Test Images

- **`small_100x100.jpg`**
  - Dimensions: 100x100 pixels
  - Content: Any character image at this resolution
  - Tests: Small image handling

- **`medium_4000x4000.jpg`**
  - Dimensions: 4000x4000 pixels
  - Content: Any character image at this resolution
  - Tests: Medium/standard photo size handling

- **`large_8000x8000.jpg`**
  - Dimensions: 8000x8000 pixels
  - Content: Any character image at this resolution
  - Tests: Large image handling (important for 70k+ photo library)

## Edge Case Test Images

- **`empty_white_image.jpg`**
  - Should contain: Blank white or very light image with no discernible content
  - Tests: Empty/invalid image handling

- **`very_dark_image.jpg`**
  - Should contain: Very dark or low-contrast image that's hard to analyze
  - Tests: Poor quality image handling

## Generic Test Images

- **`generic_test_photo.jpg`**
  - Can contain: Any valid photo
  - Used for: API timeout, retry, and connection tests

- **`test_character_1.jpg`**, **`test_character_2.jpg`**
  - Can contain: Any character images
  - Used for: General testing

## Batch Processing Test Images

- **`photo_001.jpg`** through **`photo_010.jpg`**
  - Can contain: Mix of matching and non-matching characters
  - Suggested mix: 
    - photo_001-003: Matching characters (blonde/yellow + fox)
    - photo_004-006: Non-matching characters
    - photo_007-010: Edge cases
  - Used for: Batch processing and album management tests

## Image Requirements

1. **Format**: All images should be valid JPEG files
2. **Size**: Vary sizes as indicated, but keep file sizes reasonable (< 5MB each except for large test)
3. **Content**: Anime/manga style characters work best for the classification rules
4. **Quality**: Use decent quality images except where testing poor quality handling

## Recommended Sources

For test images, you might consider:
- Screenshots from anime (Reference-san for positive matches)
- AI-generated character images with specific features
- Fan art with clear character features
- Stock photos for generic test cases

## Important Notes

1. The classification rules look for:
   - Hair color: "yellow" or "blonde" (case-insensitive)
   - Fox features: "fox ears" and/or "fox tail"
   - Both conditions must be met for a positive match (match_all=true)

2. Test images should be clear enough that a vision model can identify these features

3. For accurate testing, ensure images truly match their filename descriptions

4. Keep backup copies of good test images once you find them

## Testing Without Real Images

The current placeholder images are minimal valid JPEGs (1x1 pixel) that will allow tests to run but will likely fail classification. To properly test:

1. Replace placeholders with real images matching descriptions
2. Or temporarily mock the provider responses for logic testing
3. Or use a subset of real images for critical path testing

Remember: These tests will be validating a system processing 70,000+ photos, so having good test images is important for reliability!