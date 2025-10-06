"""Unit tests for configuration management - FIXED VERSION."""

import pytest
import json
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from visualalbumsorter.core.config import (
    Config, TaskConfig, ProviderConfig, 
    AlbumConfig, ProcessingConfig, StorageConfig, LoggingConfig,
    load_config, get_default_config
)


class TestTaskConfig:
    """Test TaskConfig data class."""
    
    def test_task_config_creation(self):
        """Test creating TaskConfig with all fields."""
        config = TaskConfig(
            name="Test Task",
            description="Test task description",  # Added required field
            prompt="Test prompt",
            classification_rules={
                "type": "regex_match",
                "rules": [{"name": "test", "pattern": r"\btest\b"}]
            }
        )
        
        assert config.name == "Test Task"
        assert config.description == "Test task description"
        assert config.prompt == "Test prompt"
        assert config.classification_rules["type"] == "regex_match"
    
    def test_task_config_validation(self):
        """Test TaskConfig validation."""
        # Valid config should not raise
        config = TaskConfig(
            name="Test",
            description="Description",  # Added required field
            prompt="Prompt",
            classification_rules={"type": "always_yes"}
        )
        assert config is not None


class TestProviderConfig:
    """Test ProviderConfig data class."""
    
    def test_provider_config_creation(self):
        """Test creating ProviderConfig."""
        config = ProviderConfig(
            type="ollama",
            settings={
                "model": "test-model",
                "api_url": "http://localhost:11434"
            }
        )
        
        assert config.type == "ollama"
        assert config.settings["model"] == "test-model"
    
    def test_provider_config_defaults(self):
        """Test ProviderConfig with minimal settings."""
        config = ProviderConfig(type="ollama", settings={})
        assert config.type == "ollama"
        assert isinstance(config.settings, dict)


class TestAlbumConfig:
    """Test AlbumConfig data class."""
    
    def test_album_config_creation(self):
        """Test creating AlbumConfig."""
        config = AlbumConfig(
            name="Test_Album",
            create_if_missing=True
        )
        
        assert config.name == "Test_Album"
        assert config.create_if_missing is True
    
    def test_album_config_defaults(self):
        """Test AlbumConfig default values."""
        config = AlbumConfig(name="Album")
        assert config.name == "Album"
        assert config.create_if_missing is True  # Default should be True


class TestProcessingConfig:
    """Test ProcessingConfig data class."""
    
    def test_processing_config_creation(self):
        """Test creating ProcessingConfig."""
        config = ProcessingConfig(
            batch_size=50,
            album_update_frequency=10,
            skip_types=['HEIC', 'GIF'],
            skip_videos=True,
            debug_mode=False,
            debug_limit=5
        )
        
        assert config.batch_size == 50
        assert config.album_update_frequency == 10
        assert 'HEIC' in config.skip_types
        assert config.skip_videos is True
    
    def test_processing_config_defaults(self):
        """Test ProcessingConfig default values."""
        config = ProcessingConfig()
        assert config.batch_size == 100  # Default
        assert config.skip_videos is True  # Default


class TestStorageConfig:
    """Test StorageConfig data class."""
    
    def test_storage_config_creation(self):
        """Test creating StorageConfig."""
        config = StorageConfig(
            temp_dir="~/Pictures/Test",
            state_file="state.json",
            done_file="done.txt"
        )
        
        assert config.temp_dir == Path("~/Pictures/Test").expanduser()
        assert config.state_file == "state.json"
        assert config.done_file == "done.txt"
    
    def test_storage_config_path_expansion(self):
        """Test path expansion in StorageConfig."""
        config = StorageConfig(temp_dir="~/test_dir")
        # Path expansion is done in __post_init__
        assert isinstance(config.temp_dir, Path)


class TestLoggingConfig:
    """Test LoggingConfig data class."""
    
    def test_logging_config_creation(self):
        """Test creating LoggingConfig."""
        config = LoggingConfig(
            level="DEBUG",
            format="%(message)s",
            console=True,
            file=False
        )
        
        assert config.level == "DEBUG"
        assert config.format == "%(message)s"
        assert config.console is True
        assert config.file is False
    
    def test_logging_config_defaults(self):
        """Test LoggingConfig default values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.console is True
        assert config.file is True


class TestConfig:
    """Test main Config class."""
    
    def test_config_from_dict_valid(self):
        """Test creating Config from valid dictionary."""
        data = {
            "task": {
                "name": "Test Task",
                "description": "Test description",  # Added required field
                "prompt": "Test prompt",
                "classification_rules": {"type": "always_yes"}
            },
            "provider": {
                "type": "ollama",
                "settings": {"model": "test-model"}
            },
            "album": {
                "name": "Test_Album"
            },
            "processing": {
                "batch_size": 50
            },
            "storage": {
                "temp_dir": "/tmp/test"
            },
            "logging": {  # Changed from logging_config to logging
                "level": "INFO"
            }
        }
        
        config = Config.from_dict(data)
        
        assert config.task.name == "Test Task"
        assert config.provider.type == "ollama"
        assert config.album.name == "Test_Album"
        assert config.processing.batch_size == 50
        assert config.storage.temp_dir == Path("/tmp/test")
    
    def test_config_from_dict_with_defaults(self):
        """Test Config creation fills in defaults."""
        minimal_data = {
            "task": {
                "name": "Task",
                "description": "Description",  # Added required field
                "prompt": "Prompt",
                "classification_rules": {"type": "always_yes"}
            },
            "provider": {
                "type": "ollama",
                "settings": {}
            },
            "album": {
                "name": "Album"
            },
            "processing": {},
            "storage": {
                "temp_dir": "/tmp/test"
            },
            "logging": {}  # Changed from logging_config to logging
        }
        
        config = Config.from_dict(minimal_data)
        
        # Check defaults were applied
        assert config.processing.batch_size == 100
        assert config.storage.state_file == "state.json"
        assert config.storage.done_file == "done.txt"
    
    def test_config_to_dict_roundtrip(self):
        """Test Config to dict and back maintains data."""
        original_data = {
            "task": {
                "name": "Test",
                "description": "Test description",  # Added required field
                "prompt": "Prompt",
                "classification_rules": {"type": "regex_match", "rules": []}
            },
            "provider": {
                "type": "lm_studio",
                "settings": {"model": "model", "api_url": "http://localhost:1234"}
            },
            "album": {"name": "Album"},
            "processing": {"batch_size": 75},
            "storage": {"temp_dir": "/tmp/test"},
            "logging": {}  # Changed from logging_config to logging
        }
        
        config = Config.from_dict(original_data)
        exported_data = config.to_dict()
        config2 = Config.from_dict(exported_data)
        
        assert config.task.name == config2.task.name
        assert config.provider.type == config2.provider.type
        assert config.processing.batch_size == config2.processing.batch_size
    
    def test_config_get_state_path(self):
        """Test get_state_path method."""
        config = Config(
            task=TaskConfig("Test", "Description", "Prompt", {}),
            provider=ProviderConfig("ollama", {}),
            album=AlbumConfig("Album"),
            processing=ProcessingConfig(),
            storage=StorageConfig(
                temp_dir="/tmp/test",
                state_file="custom_state.json"
            ),
            logging_config=LoggingConfig()
        )
        
        state_path = config.get_state_path()
        assert state_path == Path("/tmp/test/custom_state.json")
    
    def test_config_get_done_path(self):
        """Test get_done_path method."""
        config = Config(
            task=TaskConfig("Test", "Description", "Prompt", {}),
            provider=ProviderConfig("ollama", {}),
            album=AlbumConfig("Album"),
            processing=ProcessingConfig(),
            storage=StorageConfig(
                temp_dir="/tmp/test",
                done_file="custom_done.txt"
            ),
            logging_config=LoggingConfig()
        )
        
        done_path = config.get_done_path()
        assert done_path == Path("/tmp/test/custom_done.txt")
    
    def test_config_validation_invalid_provider(self):
        """Test Config validation with invalid provider type."""
        data = {
            "task": {
                "name": "Test",
                "description": "Description",  # Added required field
                "prompt": "Test",
                "classification_rules": {"type": "always_yes"}
            },
            "provider": {
                "type": "invalid_provider",  # Not a valid provider
                "settings": {}
            },
            "album": {"name": "Album"},
            "processing": {},
            "storage": {"temp_dir": "/tmp/test"},
            "logging": {}  # Changed from logging_config to logging
        }
        
        # Should still create config, validation happens elsewhere
        config = Config.from_dict(data)
        assert config.provider.type == "invalid_provider"


class TestConfigLoading:
    """Test configuration file loading."""
    
    def test_load_config_from_file(self, tmp_path):
        """Test loading configuration from JSON file."""
        config_data = {
            "task": {
                "name": "File Task",
                "description": "File description",  # Added required field
                "prompt": "File prompt",
                "classification_rules": {"type": "always_no"}
            },
            "provider": {
                "type": "mlx_vlm",
                "settings": {"model": "mlx-model"}
            },
            "album": {"name": "File_Album"},
            "processing": {},
            "storage": {"temp_dir": str(tmp_path / "storage")},
            "logging": {}  # Changed from logging_config to logging
        }
        
        config_file = tmp_path / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = load_config(config_file)
        
        assert config.task.name == "File Task"
        assert config.provider.type == "mlx_vlm"
        assert config.album.name == "File_Album"
    
    def test_load_config_file_not_found(self):
        """Test loading config from non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/config.json"))
    
    def test_load_config_invalid_json(self, tmp_path):
        """Test loading config from invalid JSON file."""
        config_file = tmp_path / "invalid.json"
        with open(config_file, 'w') as f:
            f.write("{ invalid json content")
        
        with pytest.raises(json.JSONDecodeError):
            load_config(config_file)
    
    def test_get_default_config(self):
        """Test getting default configuration."""
        default = get_default_config()
        
        assert isinstance(default, dict)
        assert "task" in default
        assert "provider" in default
        assert "album" in default
        assert "processing" in default
        assert "storage" in default
        assert "logging" in default  # Changed from logging_config to logging
        
        # Check some default values
        assert default["processing"]["batch_size"] == 100
        assert default["processing"]["skip_videos"] is True


class TestConfigEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_config_empty_classification_rules(self):
        """Test config with empty classification rules."""
        data = {
            "task": {
                "name": "Test",
                "description": "Description",  # Added required field
                "prompt": "Test",
                "classification_rules": {}
            },
            "provider": {"type": "ollama", "settings": {}},
            "album": {"name": "Album"},
            "processing": {},
            "storage": {"temp_dir": "/tmp/test"},
            "logging": {}  # Changed from logging_config to logging
        }
        
        config = Config.from_dict(data)
        assert config.task.classification_rules == {}
    
    def test_config_special_characters_in_album_name(self):
        """Test config with special characters in album name."""
        data = {
            "task": {
                "name": "Test",
                "description": "Description",  # Added required field
                "prompt": "Test",
                "classification_rules": {"type": "always_yes"}
            },
            "provider": {"type": "ollama", "settings": {}},
            "album": {"name": "Test!@#$%^&*()_Album"},
            "processing": {},
            "storage": {"temp_dir": "/tmp/test"},
            "logging": {}  # Changed from logging_config to logging
        }
        
        config = Config.from_dict(data)
        assert config.album.name == "Test!@#$%^&*()_Album"
    
    def test_config_very_large_batch_size(self):
        """Test config with very large batch size."""
        data = {
            "task": {
                "name": "Test",
                "description": "Description",  # Added required field
                "prompt": "Test",
                "classification_rules": {"type": "always_yes"}
            },
            "provider": {"type": "ollama", "settings": {}},
            "album": {"name": "Album"},
            "processing": {"batch_size": 10000},
            "storage": {"temp_dir": "/tmp/test"},
            "logging": {}  # Changed from logging_config to logging
        }
        
        config = Config.from_dict(data)
        assert config.processing.batch_size == 10000
    
    def test_config_negative_batch_size(self):
        """Test config with negative batch size."""
        data = {
            "task": {
                "name": "Test",
                "description": "Description",  # Added required field
                "prompt": "Test",
                "classification_rules": {"type": "always_yes"}
            },
            "provider": {"type": "ollama", "settings": {}},
            "album": {"name": "Album"},
            "processing": {"batch_size": -1},
            "storage": {"temp_dir": "/tmp/test"},
            "logging": {}  # Changed from logging_config to logging
        }
        
        # Should accept it, validation happens elsewhere
        config = Config.from_dict(data)
        assert config.processing.batch_size == -1
