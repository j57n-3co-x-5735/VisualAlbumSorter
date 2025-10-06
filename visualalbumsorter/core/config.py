"""Configuration management for photo sorter."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TaskConfig:
    """Task-specific configuration."""
    name: str
    description: str
    prompt: str
    classification_rules: Dict[str, Any]


@dataclass
class ProviderConfig:
    """Model provider configuration."""
    type: str
    settings: Dict[str, Any]


@dataclass
class AlbumConfig:
    """Photo album configuration."""
    name: str
    create_if_missing: bool = True


@dataclass
class ProcessingConfig:
    """Processing behavior configuration."""
    batch_size: int = 100
    album_update_frequency: int = 5
    skip_types: List[str] = field(default_factory=lambda: ["HEIC", "GIF"])
    skip_videos: bool = True
    debug_mode: bool = False
    debug_limit: int = 1


@dataclass
class StorageConfig:
    """Storage paths configuration."""
    temp_dir: Path
    state_file: str = "state.json"
    done_file: str = "done.txt"
    log_file: str = "photo_sorter.log"
    
    def __post_init__(self):
        if isinstance(self.temp_dir, str):
            self.temp_dir = Path(self.temp_dir).expanduser()


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    console: bool = True
    file: bool = True


@dataclass
class Config:
    """Complete application configuration."""
    task: TaskConfig
    provider: ProviderConfig
    album: AlbumConfig
    processing: ProcessingConfig
    storage: StorageConfig
    logging_config: LoggingConfig
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create Config from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            Config instance
        """
        return cls(
            task=TaskConfig(**data['task']),
            provider=ProviderConfig(**data['provider']),
            album=AlbumConfig(**data['album']),
            processing=ProcessingConfig(**data['processing']),
            storage=StorageConfig(**data['storage']),
            logging_config=LoggingConfig(**data['logging'])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Config to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            'task': self.task.__dict__,
            'provider': self.provider.__dict__,
            'album': self.album.__dict__,
            'processing': self.processing.__dict__,
            'storage': {
                **self.storage.__dict__,
                'temp_dir': str(self.storage.temp_dir)
            },
            'logging': self.logging_config.__dict__
        }
    
    def setup_logging(self):
        """Configure logging based on config settings."""
        handlers = []
        
        if self.logging_config.console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter(self.logging_config.format)
            )
            handlers.append(console_handler)
        
        if self.logging_config.file:
            log_path = self.storage.temp_dir / self.storage.log_file
            self.storage.temp_dir.mkdir(exist_ok=True, parents=True)
            
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(
                logging.Formatter(self.logging_config.format)
            )
            handlers.append(file_handler)
        
        logging.basicConfig(
            level=getattr(logging, self.logging_config.level),
            handlers=handlers
        )
    
    def get_state_path(self) -> Path:
        """Get full path to state file."""
        return self.storage.temp_dir / self.storage.state_file
    
    def get_done_path(self) -> Path:
        """Get full path to done file."""
        return self.storage.temp_dir / self.storage.done_file


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file.
    
    Args:
        config_path: Path to configuration file. If None, looks for:
                    1. config.json in current directory
                    2. ~/.photo_sorter/config.json
                    3. Uses default configuration
    
    Returns:
        Config instance
        
    Raises:
        FileNotFoundError: If specified config_path doesn't exist
        ValueError: If configuration is invalid
    """
    if config_path:
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        logger.info(f"Loading configuration from {config_path}")
        with open(config_path) as f:
            data = json.load(f)
    else:
        # Try to find configuration file
        search_paths = [
            Path("config.json"),
            Path("~/.photo_sorter/config.json").expanduser(),
        ]
        
        for path in search_paths:
            if path.exists():
                logger.info(f"Found configuration at {path}")
                with open(path) as f:
                    data = json.load(f)
                break
        else:
            # Use default configuration
            logger.warning("No configuration file found, using defaults")
            data = get_default_config()
    
    try:
        config = Config.from_dict(data)
        logger.info(f"Loaded configuration for task: {config.task.name}")
        return config
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")


def get_default_config() -> Dict[str, Any]:
    """Get default configuration dictionary.
    
    Returns:
        Default configuration
    """
    return {
        "task": {
            "name": "Default Image Classification",
            "description": "Basic image classification task",
            "prompt": "Describe what you see in this image.",
            "classification_rules": {
                "type": "always_no",
                "rules": [],
                "match_all": True
            }
        },
        "provider": {
            "type": "ollama",
            "settings": {
                "model": "qwen2.5vl:3b",
                "api_url": "http://127.0.0.1:11434/api/generate",
                "max_retries": 3,
                "timeout": 30
            }
        },
        "album": {
            "name": "Sorted_Photos",
            "create_if_missing": True
        },
        "processing": {
            "batch_size": 100,
            "album_update_frequency": 5,
            "skip_types": ["HEIC", "GIF"],
            "skip_videos": True,
            "debug_mode": False,
            "debug_limit": 1
        },
        "storage": {
            "temp_dir": "~/Pictures/PhotoSorterTemp",
            "state_file": "state.json",
            "done_file": "done.txt",
            "log_file": "photo_sorter.log"
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "console": True,
            "file": True
        }
    }