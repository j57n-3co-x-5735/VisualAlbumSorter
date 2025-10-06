#!/bin/bash

# Create minimal valid JPEG header (smallest possible JPEG)
# This is a 1x1 pixel JPEG in hex
JPEG_HEX="FFD8FFE000104A46494600010101006000600000FFDB004300080606070605080707070909080A0C140D0C0B0B0C1912130F141D1A1F1E1D1A1C1C20242E2720222C231C1C2837292C30313434341F27393D38323C2E333432FFDB0043010909090C0B0C180D0D1832211C213232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232323232FFC0001108000100010301220002110103110100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000FFD9"

# Create placeholder images
echo "Creating placeholder test images..."

# Character classification tests
echo "blonde_hair_with_fox_ears.jpg - Character with blonde/yellow hair AND fox ears"
echo $JPEG_HEX | xxd -r -p > blonde_hair_with_fox_ears.jpg

echo "yellow_hair_with_fox_ears_and_tail.jpg - Character with yellow hair AND fox ears AND fox tail"
echo $JPEG_HEX | xxd -r -p > yellow_hair_with_fox_ears_and_tail.jpg

echo "black_hair_no_fox_features.jpg - Character with black hair, NO fox features"
echo $JPEG_HEX | xxd -r -p > black_hair_no_fox_features.jpg

echo "blonde_hair_no_fox_ears.jpg - Character with blonde hair but NO fox ears"
echo $JPEG_HEX | xxd -r -p > blonde_hair_no_fox_ears.jpg

echo "fox_ears_but_black_hair.jpg - Character with fox ears but black/dark hair"
echo $JPEG_HEX | xxd -r -p > fox_ears_but_black_hair.jpg

# Regex pattern tests
echo "yellow_fox_complete.jpg - Character with 'yellow' hair and 'fox' features"
echo $JPEG_HEX | xxd -r -p > yellow_fox_complete.jpg

echo "yellowish_not_yellow.jpg - Character with 'yellowish' hair (not exact 'yellow' match)"
echo $JPEG_HEX | xxd -r -p > yellowish_not_yellow.jpg

echo "fox_like_features.jpg - Character with 'fox-like' or 'foxlike' features"
echo $JPEG_HEX | xxd -r -p > fox_like_features.jpg

# Complex tests
echo "complex_character_multiple_features.jpg - Character with many features"
echo $JPEG_HEX | xxd -r -p > complex_character_multiple_features.jpg

# Size tests
echo "small_100x100.jpg - Small 100x100 pixel image"
echo $JPEG_HEX | xxd -r -p > small_100x100.jpg

echo "medium_4000x4000.jpg - Medium 4000x4000 pixel image"
echo $JPEG_HEX | xxd -r -p > medium_4000x4000.jpg

echo "large_8000x8000.jpg - Large 8000x8000 pixel image"
echo $JPEG_HEX | xxd -r -p > large_8000x8000.jpg

# Edge cases
echo "empty_white_image.jpg - Blank white image"
echo $JPEG_HEX | xxd -r -p > empty_white_image.jpg

echo "very_dark_image.jpg - Very dark/low contrast image"
echo $JPEG_HEX | xxd -r -p > very_dark_image.jpg

# Generic API testing
echo "generic_test_photo.jpg - Generic photo for API tests"
echo $JPEG_HEX | xxd -r -p > generic_test_photo.jpg

echo "test_character_1.jpg - Test character 1"
echo $JPEG_HEX | xxd -r -p > test_character_1.jpg

echo "test_character_2.jpg - Test character 2"
echo $JPEG_HEX | xxd -r -p > test_character_2.jpg

# Reference-specific
echo "reference_character_match.jpg - Reference character (yellow/blonde hair + fox features)"
echo $JPEG_HEX | xxd -r -p > reference_character_match.jpg

echo "reference_character_nonmatch.jpg - Non-Reference character"
echo $JPEG_HEX | xxd -r -p > reference_character_nonmatch.jpg

# Batch processing
for i in {001..010}; do
    echo "photo_$i.jpg - Photo for batch processing test $i"
    echo $JPEG_HEX | xxd -r -p > "photo_$i.jpg"
done

echo ""
echo "Created placeholder images. Please replace with actual images matching descriptions!"
