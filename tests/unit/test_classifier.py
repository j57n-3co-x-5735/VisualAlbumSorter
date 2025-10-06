"""Unit tests for image classifier."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from visualalbumsorter.core.classifier import ImageClassifier
from visualalbumsorter.providers.base import VisionModelProvider


class TestImageClassifier:
    """Test ImageClassifier functionality."""
    
    @pytest.fixture
    def mock_provider(self):
        """Create a mock vision model provider."""
        provider = Mock(spec=VisionModelProvider)
        provider.classify_image = Mock(return_value="test response")
        provider.model_name = "test-model"
        return provider
    
    @pytest.fixture
    def basic_task_config(self):
        """Create a basic task configuration."""
        return {
            "name": "Test Task",
            "prompt": "Describe the image",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "test_rule", "pattern": r"\btest\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
    
    def test_classifier_initialization(self, mock_provider, basic_task_config):
        """Test classifier initialization."""
        classifier = ImageClassifier(mock_provider, basic_task_config)
        
        assert classifier.provider == mock_provider
        assert classifier.prompt == "Describe the image"
        assert classifier.rules == basic_task_config["classification_rules"]
    
    def test_classify_with_regex_match_positive(self, mock_provider):
        """Test classification with regex rules - positive match."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "rule1", "pattern": r"\bfox\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        mock_provider.classify_image.return_value = "A fox in the forest"
        
        result = classifier.classify(Path("/test.jpg"))
        
        assert result == "yes"
        mock_provider.classify_image.assert_called_once()
    
    def test_classify_with_regex_match_negative(self, mock_provider):
        """Test classification with regex rules - negative match."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "rule1", "pattern": r"\bfox\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        mock_provider.classify_image.return_value = "A cat in the forest"
        
        result = classifier.classify(Path("/test.jpg"))
        
        assert result == "no"
    
    def test_classify_with_multiple_rules_match_all(self, mock_provider):
        """Test classification with multiple rules requiring all to match."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "rule1", "pattern": r"\byellow\b", "field": "normalized_response"},
                    {"name": "rule2", "pattern": r"\bfox\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        
        # Test all match
        mock_provider.classify_image.return_value = "A yellow fox"
        assert classifier.classify(Path("/test.jpg")) == "yes"
        
        # Test partial match
        mock_provider.classify_image.return_value = "A yellow cat"
        assert classifier.classify(Path("/test.jpg")) == "no"
        
        # Test no match
        mock_provider.classify_image.return_value = "A black dog"
        assert classifier.classify(Path("/test.jpg")) == "no"
    
    def test_classify_with_multiple_rules_match_any(self, mock_provider):
        """Test classification with multiple rules requiring any to match."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "rule1", "pattern": r"\byellow\b", "field": "normalized_response"},
                    {"name": "rule2", "pattern": r"\bfox\b", "field": "normalized_response"}
                ],
                "match_all": False
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        
        # Test any match
        mock_provider.classify_image.return_value = "A yellow cat"
        assert classifier.classify(Path("/test.jpg")) == "yes"
        
        mock_provider.classify_image.return_value = "A red fox"
        assert classifier.classify(Path("/test.jpg")) == "yes"
        
        # Test no match
        mock_provider.classify_image.return_value = "A black dog"
        assert classifier.classify(Path("/test.jpg")) == "no"
    
    def test_classify_with_keyword_match(self, mock_provider):
        """Test classification with keyword matching."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "keyword_match",
                "keywords": ["fox", "yellow", "tail"],
                "match_all": False
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        
        # Test keyword found
        mock_provider.classify_image.return_value = "The animal has a fluffy tail"
        assert classifier.classify(Path("/test.jpg")) == "yes"
        
        # Test no keyword found
        mock_provider.classify_image.return_value = "A black cat"
        assert classifier.classify(Path("/test.jpg")) == "no"
    
    def test_classify_with_always_yes(self, mock_provider):
        """Test classification with always_yes rule."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "always_yes"
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        
        # Should always return yes
        mock_provider.classify_image.return_value = "Any response"
        assert classifier.classify(Path("/test.jpg")) == "yes"
        
        mock_provider.classify_image.return_value = ""
        assert classifier.classify(Path("/test.jpg")) == "error"
    
    def test_classify_with_always_no(self, mock_provider):
        """Test classification with always_no rule."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "always_no"
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        
        # Should always return no
        mock_provider.classify_image.return_value = "Perfect match"
        assert classifier.classify(Path("/test.jpg")) == "no"
        
        mock_provider.classify_image.return_value = "yes"
        assert classifier.classify(Path("/test.jpg")) == "no"
    
    def test_classify_with_custom_rules(self, mock_provider):
        """Test classification with custom rules."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "custom",
                "function": "contains_multiple_colors"
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        mock_provider.classify_image.return_value = "red, blue, and green"
        
        # Custom rules should be evaluated
        result = classifier.classify(Path("/test.jpg"))
        assert result == "no"
    
    def test_text_normalization(self, mock_provider):
        """Test response text normalization."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "rule1", "pattern": r"\byellow\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        
        # Test case insensitive matching after normalization
        test_cases = [
            "YELLOW fox",
            "Yellow Fox",
            "yElLoW fox",
            "  yellow  fox  ",  # Extra whitespace
        ]
        
        for response in test_cases:
            mock_provider.classify_image.return_value = response
            assert classifier.classify(Path("/test.jpg")) == "yes"
    
    def test_empty_response_handling(self, mock_provider):
        """Test handling of empty API responses."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "rule1", "pattern": r"\btest\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        
        # Empty response
        mock_provider.classify_image.return_value = ""
        result = classifier.classify(Path("/test.jpg"))
        assert result == "error"
        
        # None response
        mock_provider.classify_image.return_value = None
        result = classifier.classify(Path("/test.jpg"))
        assert result == "error"
    
    def test_malformed_json_response_handling(self, mock_provider):
        """Test handling of malformed JSON responses."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "rule1", "pattern": r"\byellow\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        
        # JSON response should still be parsed as text
        json_response = json.dumps({"description": "yellow fox", "confidence": 0.95})
        mock_provider.classify_image.return_value = json_response
        
        result = classifier.classify(Path("/test.jpg"))
        assert result == "yes"  # Should find "yellow" in the JSON string
    
    def test_classification_passes_retry_hint(self, mock_provider):
        """Ensure retry hint propagates to provider layer."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "always_yes"
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        mock_provider.classify_image.return_value = "anything"
        
        result = classifier.classify(Path("/test.jpg"), max_retries=5)
        
        assert result == "yes"
        mock_provider.classify_image.assert_called_once_with(Path("/test.jpg"), "Test prompt", 5)
    
    def test_classification_returns_error_on_empty_response(self, mock_provider):
        """Provider returning empty payload should yield error result."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "rule1", "pattern": r"\btest\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        mock_provider.classify_image.return_value = ""
        
        result = classifier.classify(Path("/test.jpg"), max_retries=3)
        
        assert result == "error"
        mock_provider.classify_image.assert_called_once_with(Path("/test.jpg"), "Test prompt", 3)
    
    def test_multiline_response_handling(self, mock_provider):
        """Test handling of multiline responses."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "hair", "pattern": r"\byellow\b", "field": "normalized_response"},
                    {"name": "ears", "pattern": r"\bfox\s+ears\b", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        
        multiline_response = """The character has:
        - Yellow blonde hair
        - Fox ears visible
        - Fluffy tail"""
        
        mock_provider.classify_image.return_value = multiline_response
        result = classifier.classify(Path("/test.jpg"))
        
        assert result == "yes"
    
    def test_special_characters_in_patterns(self, mock_provider):
        """Test regex patterns with special characters."""
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "test", "pattern": r"fox[\s-]?like", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_provider, task_config)
        
        test_cases = [
            ("foxlike ears", "yes"),
            ("fox-like features", "yes"),
            ("fox like appearance", "yes"),
            ("foxy ears", "no"),
        ]
        
        for response, expected in test_cases:
            mock_provider.classify_image.return_value = response
            result = classifier.classify(Path("/test.jpg"))
            assert result == expected
    
    def test_get_stats(self, mock_provider, basic_task_config):
        """Test getting classifier statistics."""
        classifier = ImageClassifier(mock_provider, basic_task_config)
        
        mock_provider.get_provider_name.return_value = "MockProvider"
        stats = classifier.get_stats()
        
        assert isinstance(stats, dict)
        assert stats["provider"] == "MockProvider"
        assert stats["rules_type"] == "regex_match"
        assert stats["num_rules"] == 1
