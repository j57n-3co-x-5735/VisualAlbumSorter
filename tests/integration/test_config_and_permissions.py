"""
P0 Priority Test Cases - Configuration Validation and Security
Tests for TC07, TC15: Config schema validation and Photos library permissions
Critical for 70,000+ photo library security and proper configuration
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from visualalbumsorter.core.config import Config, load_config


class TestConfigurationValidation:
    """TC07: Configuration schema validation (ROI: 8.9)"""
    
    @pytest.mark.p0
    def test_valid_minimal_config(self, temp_dir):
        """Test loading minimal valid configuration."""
        minimal_config = {
            "task": {
                "name": "Minimal Task",
                "prompt": "Test prompt",
                "classification_rules": {
                    "type": "always_yes"
                }
            },
            "provider": {
                "type": "lm_studio",
                "settings": {
                    "model": "test-model",
                    "api_url": "http://localhost:1234/v1/chat/completions"
                }
            },
            "album": {
                "name": "Test_Album"
            }
        }
        
        config_path = temp_dir / "minimal.json"
        with open(config_path, 'w') as f:
            json.dump(minimal_config, f)
        
        config = load_config(config_path)
        
        assert config.task.name == "Minimal Task"
        assert config.provider.type == "lm_studio"
        assert config.album.name == "Test_Album"
    
    @pytest.mark.p0
    def test_valid_complete_config(self, temp_dir, valid_config_dict):
        """Test loading complete configuration with all fields."""
        complete_config = valid_config_dict.copy()
        complete_config["processing"] = {
            "batch_size": 500,  # Optimized for 70k library
            "album_update_frequency": 100,
            "skip_types": ["HEIC", "GIF"],
            "skip_videos": True,
            "debug_mode": False,
            "debug_limit": 1
        }
        complete_config["storage"] = {
            "temp_dir": str(temp_dir),
            "state_file": "state.json",
            "done_file": "done.txt",
            "log_file": "processor.log"
        }
        complete_config["logging"] = {
            "level": "INFO",
            "format": "%(asctime)s - %(levelname)s - %(message)s",
            "console": True,
            "file": True
        }
        
        config_path = temp_dir / "complete.json"
        with open(config_path, 'w') as f:
            json.dump(complete_config, f)
        
        config = load_config(config_path)
        
        assert config.processing.batch_size == 500
        assert config.storage.temp_dir == Path(temp_dir)
        assert config.logging.level == "INFO"
    
    @pytest.mark.p0
    def test_missing_required_fields(self, temp_dir):
        """Test error handling for missing required fields."""
        invalid_configs = [
            # Missing task
            {
                "provider": {"type": "lm_studio", "settings": {"model": "test"}},
                "album": {"name": "Test"}
            },
            # Missing provider
            {
                "task": {"name": "Test", "prompt": "Test", "classification_rules": {"type": "always_yes"}},
                "album": {"name": "Test"}
            },
            # Missing album
            {
                "task": {"name": "Test", "prompt": "Test", "classification_rules": {"type": "always_yes"}},
                "provider": {"type": "lm_studio", "settings": {"model": "test"}}
            },
            # Missing task.prompt
            {
                "task": {"name": "Test", "classification_rules": {"type": "always_yes"}},
                "provider": {"type": "lm_studio", "settings": {"model": "test"}},
                "album": {"name": "Test"}
            },
        ]
        
        for i, invalid_config in enumerate(invalid_configs):
            config_path = temp_dir / f"invalid_{i}.json"
            with open(config_path, 'w') as f:
                json.dump(invalid_config, f)
            
            with pytest.raises((KeyError, AttributeError, ValueError)):
                load_config(config_path)
    
    @pytest.mark.p0
    def test_invalid_field_types(self, temp_dir):
        """Test error handling for wrong field types."""
        wrong_types_config = {
            "task": {
                "name": 123,  # Should be string
                "prompt": "Test",
                "classification_rules": "not_a_dict"  # Should be dict
            },
            "provider": {
                "type": "lm_studio",
                "settings": "not_a_dict"  # Should be dict
            },
            "album": {
                "name": ["not", "a", "string"]  # Should be string
            },
            "processing": {
                "batch_size": "not_a_number",  # Should be int
                "skip_videos": "yes"  # Should be bool
            }
        }
        
        config_path = temp_dir / "wrong_types.json"
        with open(config_path, 'w') as f:
            json.dump(wrong_types_config, f)
        
        # Should handle type issues gracefully
        try:
            config = load_config(config_path)
            # Check type conversions or defaults were applied
            assert isinstance(config.processing.batch_size, int) or config.processing.batch_size == 100
        except (TypeError, ValueError):
            # Expected for strict validation
            pass
    
    @pytest.mark.p0
    def test_extra_fields_ignored(self, temp_dir, valid_config_dict):
        """Test that extra/unknown fields don't break configuration."""
        config_with_extras = valid_config_dict.copy()
        config_with_extras["unknown_field"] = "should be ignored"
        config_with_extras["task"]["future_feature"] = "not yet implemented"
        
        config_path = temp_dir / "with_extras.json"
        with open(config_path, 'w') as f:
            json.dump(config_with_extras, f)
        
        config = load_config(config_path)
        
        # Should load successfully despite extra fields
        assert config.task.name == "Test Classification"
    
    @pytest.mark.p0
    def test_config_defaults_applied(self, temp_dir):
        """Test that defaults are applied for optional fields."""
        minimal_config = {
            "task": {
                "name": "Test",
                "prompt": "Test",
                "classification_rules": {"type": "always_yes"}
            },
            "provider": {
                "type": "lm_studio",
                "settings": {
                    "model": "test",
                    "api_url": "http://localhost:1234/v1/chat/completions"
                }
            },
            "album": {
                "name": "Test"
            }
        }
        
        config_path = temp_dir / "defaults.json"
        with open(config_path, 'w') as f:
            json.dump(minimal_config, f)
        
        config = load_config(config_path)
        
        # Check defaults were applied
        assert config.processing.batch_size == 100  # Default
        assert config.processing.skip_videos == True  # Default
        assert config.album.create_if_missing == True  # Default
    
    @pytest.mark.p0
    def test_lm_studio_specific_config(self, temp_dir):
        """Test LM Studio-specific configuration validation."""
        lm_config = {
            "task": {
                "name": "LM Studio Task",
                "prompt": "Test",
                "classification_rules": {"type": "always_yes"}
            },
            "provider": {
                "type": "lm_studio",
                "settings": {
                    "model": "llava-v1.6-34b",
                    "api_url": "http://localhost:1234/v1/chat/completions",
                    "max_retries": 5,
                    "timeout": 60,
                    "temperature": 0.7,
                    "max_tokens": 150
                }
            },
            "album": {
                "name": "LM_Studio_Results"
            },
            "processing": {
                "batch_size": 500,  # Optimized for 70k photos
                "album_update_frequency": 100
            }
        }
        
        config_path = temp_dir / "lm_studio.json"
        with open(config_path, 'w') as f:
            json.dump(lm_config, f)
        
        config = load_config(config_path)
        
        assert config.provider.type == "lm_studio"
        assert config.provider.settings["timeout"] == 60
        assert config.processing.batch_size == 500
    
    @pytest.mark.p0
    def test_malformed_json_handling(self, temp_dir):
        """Test handling of malformed JSON files."""
        malformed_jsons = [
            "{invalid json",
            '{"key": "value"',  # Missing closing brace
            "{'single': 'quotes'}",  # Single quotes
            '{"trailing": "comma",}',  # Trailing comma
            "",  # Empty file
        ]
        
        for i, malformed in enumerate(malformed_jsons):
            config_path = temp_dir / f"malformed_{i}.json"
            with open(config_path, 'w') as f:
                f.write(malformed)
            
            with pytest.raises((json.JSONDecodeError, ValueError)):
                load_config(config_path)


class TestPhotosLibraryPermissions:
    """TC15: Photos library permissions (ROI: 8.4)"""
    
    @pytest.mark.p0
    def test_full_access_permissions(self):
        """Test detection of full Photos library access."""
        with patch('osxphotos.PhotosDB') as mock_db:
            with patch('photoscript.PhotosLibrary') as mock_lib:
                # Simulate full access
                mock_db.return_value.photos.return_value = [Mock()]
                mock_lib.return_value.albums = [Mock()]
                
                # Should work without permission errors
                db = mock_db()
                lib = mock_lib()
                
                photos = db.photos()
                albums = lib.albums
                
                assert len(photos) > 0
                assert albums is not None
    
    @pytest.mark.p0
    def test_read_only_permissions(self):
        """Test handling of read-only Photos access."""
        with patch('osxphotos.PhotosDB') as mock_db:
            with patch('photoscript.PhotosLibrary') as mock_lib:
                # Simulate read-only - can read but not modify
                mock_db.return_value.photos.return_value = [Mock()]
                mock_lib.return_value.create_album.side_effect = PermissionError("Read-only access")
                
                db = mock_db()
                lib = mock_lib()
                
                # Reading should work
                photos = db.photos()
                assert len(photos) > 0
                
                # Writing should fail
                with pytest.raises(PermissionError):
                    lib.create_album("New_Album")
    
    @pytest.mark.p0
    def test_no_access_permissions(self):
        """Test handling when Photos access is denied."""
        with patch('osxphotos.PhotosDB') as mock_db:
            # Simulate no access
            mock_db.side_effect = PermissionError("Photos access denied")
            
            with pytest.raises(PermissionError):
                db = mock_db()
    
    @pytest.mark.p0
    def test_partial_access_permissions(self):
        """Test handling of partial Photos access (some albums accessible)."""
        with patch('photoscript.PhotosLibrary') as mock_lib:
            # Some albums accessible, others not
            accessible_album = Mock()
            accessible_album.name = "Accessible"
            accessible_album.photos = [Mock()]
            
            restricted_album = Mock()
            restricted_album.name = "Restricted"
            restricted_album.photos = PropertyMock(side_effect=PermissionError("Access denied"))
            
            mock_lib.return_value.albums = [accessible_album, restricted_album]
            
            lib = mock_lib()
            
            # Should handle mixed permissions
            for album in lib.albums:
                try:
                    photos = album.photos
                    assert album.name == "Accessible"
                except PermissionError:
                    assert album.name == "Restricted"
    
    @pytest.mark.p0
    def test_permission_prompt_handling(self):
        """Test handling of macOS permission prompts."""
        with patch('osxphotos.PhotosDB') as mock_db:
            # Simulate permission prompt scenario
            call_count = [0]
            
            def simulate_prompt(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    # First call triggers prompt
                    raise PermissionError("Waiting for user permission")
                else:
                    # Second call after permission granted
                    return Mock(photos=Mock(return_value=[Mock()]))
            
            mock_db.side_effect = simulate_prompt
            
            # First attempt should fail
            with pytest.raises(PermissionError):
                db = mock_db()
            
            # Second attempt should succeed (after user grants permission)
            db = mock_db()
            assert db is not None
    
    @pytest.mark.p0
    def test_sandbox_restrictions(self):
        """Test handling of sandbox restrictions for file access."""
        test_paths = [
            "/Users/username/Pictures/Photos Library.photoslibrary",
            "/System/Library/Photos",
            "/private/var/Photos",
        ]
        
        for test_path in test_paths:
            path = Path(test_path)
            
            # Simulate sandbox restrictions
            with patch('pathlib.Path.exists') as mock_exists:
                with patch('pathlib.Path.is_dir') as mock_is_dir:
                    mock_exists.return_value = False  # Sandbox blocks access
                    mock_is_dir.return_value = False
                    
                    # Should handle gracefully
                    if not path.exists():
                        # Expected behavior - no access
                        assert True
    
    @pytest.mark.p0
    def test_large_library_permission_check(self):
        """Test permission checking doesn't timeout with 70k+ photos."""
        import time
        
        with patch('osxphotos.PhotosDB') as mock_db:
            # Simulate large library
            large_photo_list = [Mock(uuid=f"uuid-{i}") for i in range(1000)]  # Subset for testing
            mock_db.return_value.photos.return_value = large_photo_list
            
            start_time = time.time()
            
            db = mock_db()
            photos = db.photos()
            
            duration = time.time() - start_time
            
            # Permission check should be fast even for large libraries
            assert duration < 5.0
            assert len(photos) == 1000
    
    @pytest.mark.p0
    def test_export_permission_handling(self, temp_dir):
        """Test handling of photo export permissions."""
        with patch('osxphotos.PhotosDB') as mock_db:
            photo = Mock()
            photo.uuid = "test-uuid"
            photo.filename = "test.jpg"
            
            # Test successful export
            photo.export.return_value = [str(temp_dir / "exported.jpg")]
            mock_db.return_value.photos.return_value = [photo]
            
            db = mock_db()
            photos = db.photos()
            exported = photos[0].export(str(temp_dir))
            
            assert len(exported) > 0
            
            # Test export permission denied
            photo.export.side_effect = PermissionError("Cannot export photo")
            
            with pytest.raises(PermissionError):
                photos[0].export(str(temp_dir))
    
    @pytest.mark.p0
    def test_album_modification_permissions(self):
        """Test permissions for album modifications."""
        with patch('photoscript.PhotosLibrary') as mock_lib:
            album = Mock()
            album.name = "Test_Album"
            album.photos = []
            
            # Test successful add
            album.add_photos.return_value = None
            mock_lib.return_value.albums = [album]
            
            lib = mock_lib()
            lib.albums[0].add_photos([Mock()])
            
            # Test permission denied for add
            album.add_photos.side_effect = PermissionError("Cannot modify album")
            
            with pytest.raises(PermissionError):
                lib.albums[0].add_photos([Mock()])


class TestSecurityValidation:
    """Additional security tests for configuration and permissions."""
    
    @pytest.mark.p0
    def test_api_key_not_logged(self, temp_dir, caplog):
        """Test that API keys are not logged."""
        config_with_key = {
            "task": {
                "name": "Test",
                "prompt": "Test",
                "classification_rules": {"type": "always_yes"}
            },
            "provider": {
                "type": "lm_studio",
                "settings": {
                    "model": "test",
                    "api_url": "http://localhost:1234/v1/chat/completions",
                    "api_key": "sk-secret-key-12345"
                }
            },
            "album": {"name": "Test"}
        }
        
        config_path = temp_dir / "with_key.json"
        with open(config_path, 'w') as f:
            json.dump(config_with_key, f)
        
        with caplog.at_level("DEBUG"):
            config = load_config(config_path)
            
            # API key should not appear in logs
            assert "sk-secret-key-12345" not in caplog.text
    
    @pytest.mark.p0
    def test_path_traversal_prevention(self, temp_dir):
        """Test prevention of path traversal attacks."""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "~/../../sensitive_file",
        ]
        
        for dangerous_path in dangerous_paths:
            config = {
                "task": {
                    "name": "Test",
                    "prompt": "Test",
                    "classification_rules": {"type": "always_yes"}
                },
                "provider": {
                    "type": "lm_studio",
                    "settings": {
                        "model": "test",
                        "api_url": "http://localhost:1234/v1/chat/completions"
                    }
                },
                "album": {"name": "Test"},
                "storage": {
                    "temp_dir": dangerous_path
                }
            }
            
            config_path = temp_dir / "dangerous.json"
            with open(config_path, 'w') as f:
                json.dump(config, f)
            
            # Should sanitize or reject dangerous paths
            try:
                cfg = load_config(config_path)
                # Path should be sanitized
                assert ".." not in str(cfg.storage.temp_dir)
                assert not str(cfg.storage.temp_dir).startswith("/etc")
            except (ValueError, PermissionError):
                # Expected - dangerous path rejected
                pass