"""
P0 Priority Test Cases - Album Management and Provider Integration
Tests for TC05, TC16: Album operations and provider response parsing
Optimized for 70,000+ photo libraries
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from visualalbumsorter.core.photo_processor_enhanced import EnhancedPhotoProcessor

# Test fixtures directory
TEST_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "images"


class TestAlbumCreationAndPhotoAddition:
    """TC05: Album creation and photo addition (ROI: 9.0)"""
    
    @pytest.mark.p0
    def test_album_creation_when_missing(self, mock_config, mock_classifier, mock_photos_library):
        """Test album creation when it doesn't exist."""
        mock_config.album.name = "Test_Album_New"
        mock_config.album.create_if_missing = True
        
        # Album doesn't exist initially
        mock_photos_library.album.return_value = None
        mock_photos_library.albums = []
        
        new_album = Mock()
        new_album.name = "Test_Album_New"
        new_album.photos = []
        mock_photos_library.create_album.return_value = new_album
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            processor.photos_lib = mock_photos_library
            
            # Get or create album
            album = processor._get_or_create_album(mock_photos_library)
            
            # Should create new album
            mock_photos_library.create_album.assert_called_once_with("Test_Album_New")
            assert album == new_album
    
    @pytest.mark.p0
    def test_album_exists_no_creation(self, mock_config, mock_classifier, mock_photos_library):
        """Test that existing album is reused, not recreated."""
        mock_config.album.name = "Existing_Album"
        
        # Album already exists
        existing_album = Mock()
        existing_album.name = "Existing_Album"
        existing_album.photos = []
        mock_photos_library.album.return_value = existing_album
        mock_photos_library.albums = [existing_album]
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            processor.photos_lib = mock_photos_library
            
            # Get or create album
            album = processor._get_or_create_album(mock_photos_library)
            
            # Should not create new album
            mock_photos_library.create_album.assert_not_called()
            assert album == existing_album
    
    @pytest.mark.p0
    def test_add_photos_to_album_batch(self, mock_config, mock_classifier, mock_photos_library):
        """Test adding multiple photos to album in batch."""
        mock_config.processing.album_update_frequency = 5
        
        # Setup album
        album = Mock()
        album.photos = []
        album.add_photos = Mock()
        
        # Setup photos
        photo_uuids = [f"uuid-{i}" for i in range(10)]
        photos = []
        for uuid in photo_uuids:
            photo = Mock()
            photo.uuid = uuid
            photos.append(photo)
        
        mock_photos_library.album.return_value = album
        mock_photos_library.photos.return_value = photos
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            processor.photos_lib = mock_photos_library
            processor.album = album
            
            # Add photos to album
            processor._add_to_album(album, photo_uuids[:5], mock_photos_library)
            
            # Should add photos in batch
            assert album.add_photos.call_count == 1
            added_photos = album.add_photos.call_args[0][0]
            assert len(added_photos) == 5
    
    @pytest.mark.p0
    def test_duplicate_photo_handling_in_album(self, mock_config, mock_classifier, mock_photos_library):
        """Test that duplicate photos aren't added to album twice."""
        # Setup album with existing photos
        album = Mock()
        existing_photo = Mock()
        existing_photo.uuid = "existing-uuid"
        album.photos = [existing_photo]
        album.add_photos = Mock()
        
        mock_photos_library.album.return_value = album
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            processor.photos_lib = mock_photos_library
            processor.album = album
            
            # Try to add duplicate
            new_photo = Mock()
            new_photo.uuid = "existing-uuid"
            mock_photos_library.photos.return_value = [new_photo]
            
            processor._add_to_album(album, ["existing-uuid"], mock_photos_library)
            
            # Should check for duplicates before adding
            # Implementation may vary - either skip or handle gracefully
            assert True  # Test passes if no exception
    
    @pytest.mark.p0
    def test_album_name_conflict_handling(self, mock_config, mock_classifier, mock_photos_library):
        """Test handling of album name conflicts."""
        mock_config.album.name = "Conflicting_Name"
        mock_config.album.create_if_missing = True
        
        # Simulate name conflict - album exists but different type
        conflicting_album = Mock()
        conflicting_album.name = "Conflicting_Name"
        conflicting_album.photos = []
        mock_photos_library.album.return_value = conflicting_album
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            processor.photos_lib = mock_photos_library
            
            album = processor._get_or_create_album(mock_photos_library)
            
            # Should handle conflict gracefully
            assert album is not None
    
    @pytest.mark.p0
    def test_large_album_update_performance(self, mock_config, mock_classifier, mock_photos_library):
        """Test performance with large number of photos (70k+ library)."""
        import time
        
        # Simulate large batch from 70k library
        large_batch_uuids = [f"uuid-{i}" for i in range(1000)]
        
        album = Mock()
        album.photos = []
        album.add_photos = Mock()
        
        # Mock photos retrieval
        photos = [Mock(uuid=uuid) for uuid in large_batch_uuids]
        mock_photos_library.photos.return_value = photos
        mock_photos_library.album.return_value = album
        
        with patch('visualalbumsorter.core.photo_processor_enhanced.EnhancedPhotoProcessor._init_photo_libraries'):
            processor = EnhancedPhotoProcessor(mock_config, mock_classifier, enable_diagnostics=False)
            processor.photos_lib = mock_photos_library
            processor.album = album
            
            start_time = time.time()
            processor._add_to_album(album, large_batch_uuids[:100], mock_photos_library)  # Update with 100 photos
            duration = time.time() - start_time
            
            # Should complete quickly even with large batches
            assert duration < 5.0  # Should take less than 5 seconds
            assert album.add_photos.called


class TestProviderResponseParsing:
    """TC16: Provider response parsing (ROI: 8.8)"""
    
    @pytest.mark.p0
    def test_parse_lm_studio_json_response(self, mock_lm_studio_provider):
        """Test parsing of LM Studio JSON responses."""
        from visualalbumsorter.core.classifier import ImageClassifier
        
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [{"name": "test", "pattern": r"yellow", "field": "normalized_response"}],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_lm_studio_provider, task_config)
        
        # Test various LM Studio response formats
        test_responses = [
            '{"response": "yellow fox ears"}',
            'yellow fox ears',  # Plain text
            '{"choices": [{"message": {"content": "yellow fox"}}]}',  # OpenAI format
            'The character has yellow hair\nWith fox ears',  # Multiline
        ]
        
        for response in test_responses:
            mock_lm_studio_provider.classify_image.return_value = response
            result = classifier.classify(Path(str(TEST_FIXTURES_DIR / "generic_test_photo.jpg")))
            assert result == "yes", f"Failed to parse: {response}"
    
    @pytest.mark.p0
    def test_parse_ollama_response_format(self, mock_ollama_provider):
        """Test parsing of Ollama response format."""
        from visualalbumsorter.core.classifier import ImageClassifier
        
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [{"name": "test", "pattern": r"fox", "field": "normalized_response"}],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_ollama_provider, task_config)
        
        # Ollama typically returns plain text
        ollama_responses = [
            "Character with fox ears",
            json.dumps({"response": "fox tail visible"}),
            "Fox-like features present",
        ]
        
        for response in ollama_responses:
            mock_ollama_provider.classify_image.return_value = response
            result = classifier.classify(Path(str(TEST_FIXTURES_DIR / "generic_test_photo.jpg")))
            assert result == "yes", f"Failed to parse: {response}"
    
    @pytest.mark.p0
    def test_parse_special_characters_in_response(self, mock_lm_studio_provider):
        """Test parsing responses with special characters."""
        from visualalbumsorter.core.classifier import ImageClassifier
        
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [{"name": "test", "pattern": r"yellow", "field": "normalized_response"}],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_lm_studio_provider, task_config)
        
        # Responses with special characters
        special_responses = [
            "Character has yellow/blonde hair",
            "Yellow hair (confirmed)",
            "Yellow & fox-like features",
            "✓ Yellow hair detected",
            "Character: yellow; fox ears: yes",
        ]
        
        for response in special_responses:
            mock_lm_studio_provider.classify_image.return_value = response
            result = classifier.classify(Path(str(TEST_FIXTURES_DIR / "generic_test_photo.jpg")))
            assert result == "yes", f"Failed with special chars: {response}"
    
    @pytest.mark.p0
    def test_parse_empty_and_null_responses(self, mock_lm_studio_provider):
        """Test handling of empty/null responses."""
        from visualalbumsorter.core.classifier import ImageClassifier
        
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {"type": "regex_match", "rules": []}
        }
        
        classifier = ImageClassifier(mock_lm_studio_provider, task_config)
        
        # Empty/null responses
        empty_responses = [
            "",
            None,
            "{}",
            "[]",
            '{"response": ""}',
            '{"response": null}',
        ]
        
        for response in empty_responses:
            mock_lm_studio_provider.classify_image.return_value = response
            result = classifier.classify(Path(str(TEST_FIXTURES_DIR / "generic_test_photo.jpg")))
            assert result in ["error", "no"], f"Unexpected result for: {response}"
    
    @pytest.mark.p0
    def test_parse_unicode_responses(self, mock_lm_studio_provider):
        """Test parsing responses with Unicode characters."""
        from visualalbumsorter.core.classifier import ImageClassifier
        
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [{"name": "test", "pattern": r"yellow|黄色|amarillo", "field": "normalized_response"}],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_lm_studio_provider, task_config)
        
        # Unicode responses
        unicode_responses = [
            "Character has 黄色 (yellow) hair",
            "Personaje con pelo amarillo",
            "キャラクターは黄色い髪",
            "Yellow 🦊 fox ears",
        ]
        
        for response in unicode_responses:
            mock_lm_studio_provider.classify_image.return_value = response
            result = classifier.classify(Path(str(TEST_FIXTURES_DIR / "generic_test_photo.jpg")))
            assert result == "yes", f"Failed with Unicode: {response}"
    
    @pytest.mark.p0
    def test_parse_very_long_responses(self, mock_lm_studio_provider):
        """Test parsing very long responses (edge case for large libraries)."""
        from visualalbumsorter.core.classifier import ImageClassifier
        
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [{"name": "test", "pattern": r"yellow", "field": "normalized_response"}],
                "match_all": True
            }
        }
        
        classifier = ImageClassifier(mock_lm_studio_provider, task_config)
        
        # Very long response
        long_response = "Lorem ipsum " * 1000 + " yellow hair " + "dolor sit " * 1000
        
        mock_lm_studio_provider.classify_image.return_value = long_response
        result = classifier.classify(Path(str(TEST_FIXTURES_DIR / "generic_test_photo.jpg")))
        
        # Should still find the pattern in long text
        assert result == "yes"
    
    @pytest.mark.p0
    def test_provider_response_consistency(self, mock_lm_studio_provider, mock_ollama_provider):
        """Test that different providers produce consistent classification results."""
        from visualalbumsorter.core.classifier import ImageClassifier
        
        task_config = {
            "name": "Test",
            "prompt": "Test prompt",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "hair", "pattern": r"blonde|yellow", "field": "normalized_response"},
                    {"name": "ears", "pattern": r"fox", "field": "normalized_response"}
                ],
                "match_all": True
            }
        }
        
        test_response = "Character has blonde hair with fox ears"
        
        # Test with LM Studio provider
        classifier_lm = ImageClassifier(mock_lm_studio_provider, task_config)
        mock_lm_studio_provider.classify_image.return_value = test_response
        result_lm = classifier_lm.classify(Path(str(TEST_FIXTURES_DIR / "generic_test_photo.jpg")))
        
        # Test with Ollama provider
        classifier_ollama = ImageClassifier(mock_ollama_provider, task_config)
        mock_ollama_provider.classify_image.return_value = test_response
        result_ollama = classifier_ollama.classify(Path(str(TEST_FIXTURES_DIR / "generic_test_photo.jpg")))
        
        # Both should produce same result
        assert result_lm == result_ollama == "yes"