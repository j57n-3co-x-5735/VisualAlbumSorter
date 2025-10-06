"""
P0 Priority Test Cases - Core Classification Logic
Tests for TC01, TC13: Photo classification and regex pattern matching
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import base64

from visualalbumsorter.core.classifier import ImageClassifier
from visualalbumsorter.providers.base import VisionModelProvider


class TestPhotoClassification:
    """TC01: Verify photo classification with valid images (ROI: 9.2)"""
    
    @pytest.mark.p0
    def test_classify_valid_jpg_positive_match(self, mock_ollama_provider, test_images):
        """Test classification of valid JPG with positive match."""
        # Setup
        task_config = {
            "name": "Test Task",
            "prompt": "Describe the character",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "hair", "pattern": r"\b(yellow|blonde)\b", "field": "normalized_response"},
                    {"name": "ears", "pattern": r"\bfox\s+ears?\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        mock_ollama_provider.classify_image.return_value = "Character has blonde hair with fox ears"
        
        # Execute
        result = classifier.classify(test_images['generic'])
        
        # Assert
        assert result == "yes"
        mock_ollama_provider.classify_image.assert_called_once()
    
    @pytest.mark.p0
    def test_classify_valid_jpg_negative_match(self, mock_ollama_provider, test_images):
        """Test classification of valid JPG with negative match."""
        # Setup
        task_config = {
            "name": "Test Task",
            "prompt": "Describe the character",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "hair", "pattern": r"\b(yellow|blonde)\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        mock_ollama_provider.classify_image.return_value = "Character has black hair"
        
        # Execute
        result = classifier.classify(test_images['generic'])
        
        # Assert
        assert result == "no"
    
    @pytest.mark.p0
    def test_classify_with_empty_response(self, mock_ollama_provider, test_images):
        """Test classification when provider returns empty response."""
        # Setup
        task_config = {
            "name": "Test Task",
            "prompt": "Describe the character",
            "classification_rules": {"type": "regex_match", "rules": []}
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        mock_ollama_provider.classify_image.return_value = ""
        
        # Execute
        result = classifier.classify(test_images['generic'])
        
        # Assert
        assert result == "error"
    
    @pytest.mark.p0
    @pytest.mark.parametrize("image_size,expected_time", [
        ((100, 100), 5),    # Small image
        ((4000, 4000), 5),  # Medium image
        ((8000, 8000), 5),  # Large image
    ])
    def test_classify_various_image_sizes(self, mock_ollama_provider, test_images, image_size, expected_time):
        """Test classification with various image sizes."""
        import time
        
        # Setup
        task_config = {
            "name": "Test Task",
            "prompt": "Describe the image",
            "classification_rules": {"type": "always_yes"}
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        mock_ollama_provider.classify_image.return_value = "Test response"
        
        # Execute
        start = time.time()
        # Map sizes to actual test images
        size_map = {(100, 100): 'small', (4000, 4000): 'medium', (8000, 8000): 'large'}
        image_key = size_map.get(image_size, 'generic')
        result = classifier.classify(test_images[image_key])
        duration = time.time() - start
        
        # Assert
        assert result == "yes"
        assert duration < expected_time, f"Classification took {duration}s, expected < {expected_time}s"


class TestRegexPatternMatching:
    """TC13: Regex pattern matching accuracy (ROI: 9.3)"""
    
    @pytest.mark.p0
    def test_regex_single_pattern_match(self, mock_ollama_provider, test_images):
        """Test single regex pattern matching."""
        task_config = {
            "name": "Test Task",
            "prompt": "Test",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "test", "pattern": r"\byellow\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # Test cases
        test_cases = [
            ("yellow hair", "yes"),
            ("yellowish hair", "no"),
            ("bright yellow", "yes"),
            ("yellow-green", "no"),
            ("YELLOW", "yes"),  # Should be case-insensitive after normalization
        ]
        
        for response, expected in test_cases:
            mock_ollama_provider.classify_image.return_value = response
            result = classifier.classify(test_images['generic'])
            assert result == expected, f"Failed for response: '{response}'"
    
    @pytest.mark.p0
    def test_regex_multiple_patterns_match_all(self, mock_ollama_provider, test_images):
        """Test multiple patterns with match_all=True."""
        task_config = {
            "name": "Test Task",
            "prompt": "Test",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "hair", "pattern": r"\b(yellow|blonde)\b", "field": "normalized_response"},
                    {"name": "ears", "pattern": r"\bfox\s+ears?\b", "field": "normalized_response"},
                    {"name": "tail", "pattern": r"\bfox\s+tails?\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # Test cases
        test_cases = [
            ("blonde hair with fox ears and fox tail", "yes"),
            ("blonde hair with fox ears", "no"),  # Missing tail
            ("black hair with fox ears and fox tail", "no"),  # Wrong hair
            ("blonde hair with cat ears and fox tail", "no"),  # Wrong ears
        ]
        
        for response, expected in test_cases:
            mock_ollama_provider.classify_image.return_value = response
            result = classifier.classify(test_images['generic'])
            assert result == expected, f"Failed for response: '{response}'"
    
    @pytest.mark.p0
    def test_regex_multiple_patterns_match_any(self, mock_ollama_provider, test_images):
        """Test multiple patterns with match_all=False."""
        task_config = {
            "name": "Test Task",
            "prompt": "Test",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "hair", "pattern": r"\byellow\b", "field": "normalized_response"},
                    {"name": "ears", "pattern": r"\bfox\b", "field": "normalized_response"}
                ],
                "match_all": False
            }
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # Test cases
        test_cases = [
            ("yellow hair", "yes"),
            ("fox ears", "yes"),
            ("yellow fox", "yes"),
            ("black cat", "no"),
        ]
        
        for response, expected in test_cases:
            mock_ollama_provider.classify_image.return_value = response
            result = classifier.classify(test_images['generic'])
            assert result == expected, f"Failed for response: '{response}'"
    
    @pytest.mark.p0
    def test_regex_special_characters(self, mock_ollama_provider, test_images):
        """Test regex patterns with special characters."""
        task_config = {
            "name": "Test Task",
            "prompt": "Test",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "test", "pattern": r"fox[\s-]?like", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # Test cases
        test_cases = [
            ("foxlike ears", "yes"),
            ("fox-like ears", "yes"),
            ("fox like ears", "yes"),
            ("foxy ears", "no"),
        ]
        
        for response, expected in test_cases:
            mock_ollama_provider.classify_image.return_value = response
            result = classifier.classify(test_images['generic'])
            assert result == expected, f"Failed for response: '{response}'"
    
    @pytest.mark.p0
    def test_keyword_match_rules(self, mock_ollama_provider, test_images):
        """Test keyword matching rule type."""
        task_config = {
            "name": "Test Task",
            "prompt": "Test",
            "classification_rules": {
                "type": "keyword_match",
                "keywords": ["yellow", "fox", "tail"],
                "match_all": False
            }
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # Test cases
        test_cases = [
            ("has yellow color", "yes"),
            ("fox is present", "yes"),
            ("long tail visible", "yes"),
            ("black cat", "no"),
        ]
        
        for response, expected in test_cases:
            mock_ollama_provider.classify_image.return_value = response
            result = classifier.classify(test_images['generic'])
            assert result == expected, f"Failed for response: '{response}'"
    
    @pytest.mark.p0
    def test_always_yes_rules(self, mock_ollama_provider, test_images):
        """Test always_yes rule type."""
        task_config = {
            "name": "Test Task",
            "prompt": "Test",
            "classification_rules": {"type": "always_yes"}
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # Should always return yes regardless of response
        responses = ["anything", "", "no match", "error"]
        for response in responses:
            mock_ollama_provider.classify_image.return_value = response
            result = classifier.classify(test_images['generic'])
            assert result == "yes", f"Failed for response: '{response}'"
    
    @pytest.mark.p0
    def test_always_no_rules(self, mock_ollama_provider, test_images):
        """Test always_no rule type."""
        task_config = {
            "name": "Test Task",
            "prompt": "Test",
            "classification_rules": {"type": "always_no"}
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # Should always return no regardless of response
        responses = ["perfect match", "yes", "definitely"]
        for response in responses:
            mock_ollama_provider.classify_image.return_value = response
            result = classifier.classify(test_images['generic'])
            assert result == "no", f"Failed for response: '{response}'"
    
    @pytest.mark.p0
    def test_case_sensitivity_handling(self, mock_ollama_provider, test_images):
        """Test that pattern matching handles case correctly."""
        task_config = {
            "name": "Test Task",
            "prompt": "Test",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "test", "pattern": r"\byellow\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # Test cases - should all match after normalization
        test_cases = [
            ("YELLOW hair", "yes"),
            ("Yellow hair", "yes"),
            ("yElLoW hair", "yes"),
            ("yellow hair", "yes"),
        ]
        
        for response, expected in test_cases:
            mock_ollama_provider.classify_image.return_value = response
            result = classifier.classify(test_images['generic'])
            assert result == expected, f"Failed for response: '{response}'"


class TestClassificationEdgeCases:
    """Edge cases and error scenarios for classification."""
    
    @pytest.mark.p0
    def test_classification_with_retry(self, mock_ollama_provider, test_images):
        """Test classification retry logic."""
        task_config = {
            "name": "Test Task",
            "prompt": "Test",
            "classification_rules": {"type": "always_yes"}
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # Simulate failure then success
        mock_ollama_provider.classify_image.side_effect = [
            "",  # First attempt fails
            "",  # Second attempt fails
            "Success"  # Third attempt succeeds
        ]
        
        result = classifier.classify(Path("/test.jpg"), max_retries=3)
        
        # Should succeed after retries
        assert result == "yes"
        assert mock_ollama_provider.classify_image.call_count <= 3
    
    @pytest.mark.p0
    def test_classification_with_multiline_response(self, mock_ollama_provider, test_images):
        """Test classification with multiline responses."""
        task_config = {
            "name": "Test Task",
            "prompt": "Test",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "hair", "pattern": r"\byellow\b", "field": "normalized_response"},
                    {"name": "ears", "pattern": r"\bfox\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # Multiline response
        response = """The character has:
        - Yellow blonde hair
        - Fox ears visible
        - Fluffy tail"""
        
        mock_ollama_provider.classify_image.return_value = response
        result = classifier.classify(Path("/test.jpg"))
        
        assert result == "yes"
    
    @pytest.mark.p0
    def test_classification_with_json_response(self, mock_ollama_provider, test_images):
        """Test classification with JSON responses."""
        task_config = {
            "name": "Test Task",
            "prompt": "Test",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "hair", "pattern": r"\byellow\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # JSON response
        response = json.dumps({
            "description": "Character with yellow hair",
            "confidence": 0.95
        })
        
        mock_ollama_provider.classify_image.return_value = response
        result = classifier.classify(Path("/test.jpg"))
        
        assert result == "yes"