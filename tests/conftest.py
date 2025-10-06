"""
Pytest configuration and shared fixtures for Visual Album Sorter tests.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import base64
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test fixtures directory
TEST_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "images"


# ==================== Test Image Fixtures ====================

@pytest.fixture
def test_images():
    """Provide paths to test images."""
    return {
        'blonde_with_fox': TEST_FIXTURES_DIR / "blonde_hair_with_fox_ears.jpg",
        'yellow_complete': TEST_FIXTURES_DIR / "yellow_hair_with_fox_ears_and_tail.jpg",
        'black_hair': TEST_FIXTURES_DIR / "black_hair_no_fox_features.jpg",
        'blonde_no_fox': TEST_FIXTURES_DIR / "blonde_hair_no_fox_ears.jpg",
        'fox_black_hair': TEST_FIXTURES_DIR / "fox_ears_but_black_hair.jpg",
        'reference_match': TEST_FIXTURES_DIR / "reference_character_match.jpg",
        'reference_nonmatch': TEST_FIXTURES_DIR / "reference_character_nonmatch.jpg",
        'generic': TEST_FIXTURES_DIR / "generic_test_photo.jpg",
        'small': TEST_FIXTURES_DIR / "small_100x100.jpg",
        'medium': TEST_FIXTURES_DIR / "medium_4000x4000.jpg",
        'large': TEST_FIXTURES_DIR / "large_8000x8000.jpg",
        'empty': TEST_FIXTURES_DIR / "empty_white_image.jpg",
        'dark': TEST_FIXTURES_DIR / "very_dark_image.jpg",
        'batch': [TEST_FIXTURES_DIR / f"photo_{i:03d}.jpg" for i in range(1, 11)]
    }

# ==================== Configuration Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock configuration object."""
    config = Mock()
    
    # Task configuration
    config.task.name = "Test Task"
    config.task.prompt = "Test prompt for classification"
    config.task.classification_rules = {
        "type": "regex_match",
        "rules": [
            {"name": "test_rule", "pattern": r"\btest\b", "field": "normalized_response"}
        ],
        "match_all": True
    }
    
    # Provider configuration
    config.provider.type = "ollama"
    config.provider.settings = {
        "model": "test-model",
        "api_url": "http://localhost:11434/api/generate",
        "max_retries": 3,
        "timeout": 30
    }
    
    # Album configuration
    config.album.name = "Test_Album"
    config.album.create_if_missing = True
    
    # Processing configuration
    config.processing.batch_size = 10
    config.processing.album_update_frequency = 5
    config.processing.skip_types = ['HEIC', 'GIF']
    config.processing.skip_videos = True
    config.processing.debug_mode = False
    config.processing.debug_limit = 1
    
    # Storage configuration
    config.storage.temp_dir = Path(tempfile.mkdtemp())
    config.storage.state_file = "state.json"
    config.storage.done_file = "done.txt"
    
    # Add methods
    config.get_state_path = Mock(return_value=config.storage.temp_dir / 'state.json')
    config.get_done_path = Mock(return_value=config.storage.temp_dir / 'done.txt')
    
    return config


@pytest.fixture
def valid_config_dict():
    """Return a valid configuration dictionary."""
    return {
        "task": {
            "name": "Test Classification",
            "prompt": "Describe the image",
            "classification_rules": {
                "type": "regex_match",
                "rules": [
                    {"name": "rule1", "pattern": "test", "field": "normalized_response"}
                ],
                "match_all": True
            }
        },
        "provider": {
            "type": "ollama",
            "settings": {
                "model": "test-model",
                "api_url": "http://localhost:11434/api/generate"
            }
        },
        "album": {
            "name": "Test_Album"
        },
        "processing": {
            "batch_size": 100
        },
        "storage": {
            "temp_dir": "~/Pictures/TestTemp"
        }
    }


# ==================== Provider Fixtures ====================

@pytest.fixture
def mock_ollama_provider():
    """Mock Ollama provider."""
    provider = Mock()
    provider.model_name = "test-model"
    provider.api_url = "http://localhost:11434/api/generate"
    provider.classify_image = Mock(return_value="test response with matching pattern")
    provider.check_server = Mock(return_value=True)
    return provider


@pytest.fixture
def mock_lm_studio_provider():
    """Mock LM Studio provider."""
    provider = Mock()
    provider.model_name = "test-lm-model"
    provider.api_url = "http://localhost:1234/v1/chat/completions"
    provider.classify_image = Mock(return_value="test response")
    provider.check_server = Mock(return_value=True)
    return provider


@pytest.fixture
def mock_classifier(mock_ollama_provider):
    """Mock image classifier."""
    classifier = Mock()
    classifier.provider = mock_ollama_provider
    classifier.prompt = "Test prompt"
    classifier.classify = Mock(return_value="yes")
    return classifier


# ==================== Photos Library Fixtures ====================

@pytest.fixture
def mock_photo():
    """Create a mock photo object."""
    photo = Mock()
    photo.uuid = "test-uuid-123"
    photo.filename = "test_photo.jpg"
    photo.path = "/path/to/test_photo.jpg"
    photo.ismovie = False
    photo.date = datetime.now()
    photo.export = Mock(return_value=["/tmp/exported_photo.jpg"])
    return photo


@pytest.fixture
def mock_photos_list(mock_photo):
    """Create a list of mock photos."""
    photos = []
    for i in range(10):
        photo = Mock()
        photo.uuid = f"uuid-{i}"
        photo.filename = f"photo_{i}.jpg"
        photo.path = f"/path/to/photo_{i}.jpg"
        photo.ismovie = False
        photo.date = datetime.now()
        photo.export = Mock(return_value=[f"/tmp/photo_{i}.jpg"])
        photos.append(photo)
    return photos


@pytest.fixture
def mock_photos_db(mock_photos_list):
    """Mock osxphotos PhotosDB."""
    db = Mock()
    db.photos = Mock(return_value=mock_photos_list)
    db.get_photo = Mock(side_effect=lambda uuid: next(
        (p for p in mock_photos_list if p.uuid == uuid), None
    ))
    return db


@pytest.fixture
def mock_photos_library():
    """Mock photoscript PhotosLibrary."""
    library = Mock()
    
    # Mock album
    album = Mock()
    album.name = "Test_Album"
    album.photos = []
    album.add = Mock()
    
    library.albums = [album]
    library.album = Mock(return_value=album)
    library.create_album = Mock(return_value=album)
    library.photos = Mock(return_value=[])
    
    return library


# ==================== File System Fixtures ====================

@pytest.fixture
def temp_dir():
    """Create a temporary directory that's cleaned up after test."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def temp_state_dir(temp_dir):
    """Create a temporary directory with state files."""
    state_path = temp_dir / "state.json"
    done_path = temp_dir / "done.txt"
    
    # Create empty files
    state_path.touch()
    done_path.touch()
    
    return {
        "dir": temp_dir,
        "state": state_path,
        "done": done_path
    }


@pytest.fixture
def sample_state_data():
    """Sample state data for testing."""
    return {
        "last_index": 50,
        "matches": ["uuid-1", "uuid-2", "uuid-3"],
        "batch_processed": 5,
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def corrupted_state_files(temp_dir):
    """Create various corrupted state files for testing."""
    files = {}
    
    # Invalid JSON
    invalid_json = temp_dir / "invalid.json"
    invalid_json.write_text("{invalid json content")
    files["invalid_json"] = invalid_json
    
    # Missing fields
    missing_fields = temp_dir / "missing.json"
    missing_fields.write_text('{"last_index": 10}')
    files["missing_fields"] = missing_fields
    
    # Wrong types
    wrong_types = temp_dir / "wrong_types.json"
    wrong_types.write_text('{"last_index": "not_a_number", "matches": "not_a_list"}')
    files["wrong_types"] = wrong_types
    
    return files


# ==================== Image Data Fixtures ====================

@pytest.fixture
def sample_image_base64():
    """Return a small base64-encoded test image."""
    # 1x1 pixel red PNG
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="


@pytest.fixture
def sample_images_dir(temp_dir):
    """Create a directory with sample test images."""
    images_dir = temp_dir / "images"
    images_dir.mkdir()
    
    # Create some dummy image files
    for i in range(5):
        img_path = images_dir / f"test_{i}.jpg"
        img_path.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        ))
    
    return images_dir


@pytest.fixture
def corrupted_images_dir(temp_dir):
    """Create a directory with corrupted image files."""
    images_dir = temp_dir / "corrupted"
    images_dir.mkdir()
    
    # Zero-byte file
    (images_dir / "zero_bytes.jpg").touch()
    
    # Invalid header
    (images_dir / "invalid_header.jpg").write_bytes(b"Not an image")
    
    # Truncated file
    (images_dir / "truncated.jpg").write_bytes(b"\xff\xd8\xff")  # Partial JPEG header
    
    return images_dir


# ==================== Response Mock Fixtures ====================

@pytest.fixture
def mock_api_responses():
    """Collection of mock API responses for testing."""
    return {
        "positive_match": "The character has yellow blonde hair with fox ears and a fluffy fox tail",
        "negative_match": "The character has black hair with cat ears",
        "partial_match": "The character has blonde hair but human ears",
        "empty": "",
        "error": None,
        "json_response": json.dumps({
            "response": "Yellow hair with fox ears visible"
        }),
        "multiline": "The character has:\n- Blonde hair\n- Fox ears\n- Fox tail"
    }


@pytest.fixture
def mock_network_conditions():
    """Simulate various network conditions."""
    def network_simulator(condition="normal"):
        if condition == "timeout":
            import time
            time.sleep(35)  # Exceed typical timeout
        elif condition == "intermittent":
            import random
            if random.random() < 0.5:
                raise ConnectionError("Network error")
        elif condition == "offline":
            raise ConnectionError("No connection")
        return "Normal response"
    
    return network_simulator


# ==================== Performance Testing Fixtures ====================

@pytest.fixture
def performance_timer():
    """Simple performance timer for benchmarking."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
            return self.end_time - self.start_time
        
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


@pytest.fixture
def memory_tracker():
    """Track memory usage during tests."""
    import psutil
    import os
    
    class MemoryTracker:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_memory = None
            self.peak_memory = None
        
        def start(self):
            self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            self.peak_memory = self.start_memory
        
        def update(self):
            current = self.process.memory_info().rss / 1024 / 1024
            self.peak_memory = max(self.peak_memory, current)
        
        def get_usage(self):
            current = self.process.memory_info().rss / 1024 / 1024
            return {
                "current": current,
                "start": self.start_memory,
                "peak": self.peak_memory,
                "increase": current - self.start_memory
            }
    
    return MemoryTracker()


# ==================== Utility Fixtures ====================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton instances between tests."""
    # Add any singleton resets here if needed
    yield


@pytest.fixture
def capture_logs():
    """Capture log output during tests."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Add handler to root logger
    logger = logging.getLogger()
    logger.addHandler(handler)
    
    yield log_capture
    
    # Clean up
    logger.removeHandler(handler)


# ==================== Markers and Test Helpers ====================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "network: marks tests requiring network access"
    )


# ==================== Session-level Fixtures ====================

@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def ci_environment():
    """Check if running in CI environment."""
    import os
    return os.environ.get("CI", "false").lower() == "true"