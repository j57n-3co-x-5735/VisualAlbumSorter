"""Abstract base class for vision model providers."""

from abc import ABC, abstractmethod
from pathlib import Path
import base64
import logging
from typing import Optional, Dict, Any, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


class VisionModelProvider(ABC):
    """Abstract base class for vision model providers."""
    
    def __init__(self, model_name: str, api_url: str, config: Optional[Dict[str, Any]] = None):
        """Initialize the provider.
        
        Args:
            model_name: Name of the model to use
            api_url: API endpoint URL
            config: Optional provider-specific configuration
        """
        self.model_name = model_name
        self.api_url = api_url
        self.config = config or {}
        max_size = self.config.get('max_image_size_mb')
        try:
            self.max_image_size_mb = float(max_size) if max_size is not None else 50.0
        except (TypeError, ValueError):
            logger.warning(
                "Invalid max_image_size_mb=%s for %s; falling back to 50MB",
                max_size,
                self.__class__.__name__,
            )
            self.max_image_size_mb = 50.0

        max_dimension = self.config.get('max_image_dimension_px')
        try:
            self.max_image_dimension_px = int(max_dimension) if max_dimension is not None else 0
            if self.max_image_dimension_px < 0:
                self.max_image_dimension_px = 0
        except (TypeError, ValueError):
            logger.warning(
                "Invalid max_image_dimension_px=%s for %s; disabling dimension limit",
                max_dimension,
                self.__class__.__name__,
            )
            self.max_image_dimension_px = 0
        logger.info(f"Initialized {self.__class__.__name__} with model: {model_name}")
    
    @abstractmethod
    def classify_image(self, image_path: Path, prompt: str, max_retries: int = 3) -> str:
        """Classify an image using the vision model.
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt for the model
            max_retries: Maximum number of retry attempts
            
        Returns:
            The model's response text, or empty string on error
        """
        pass
    
    @abstractmethod
    def check_server(self) -> bool:
        """Check if the model server is running and accessible.
        
        Returns:
            True if server is available, False otherwise
        """
        pass
    
    def validate_image(self, image_path: Path) -> Tuple[bool, str]:
        """Validate if image can be processed.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (is_valid, error_message). error_message is empty if valid.
        """
        try:
            # Check file exists
            if not image_path.exists():
                return False, "File does not exist"

            # Check file size if limit configured
            file_size = image_path.stat().st_size
            if file_size == 0:
                return False, "File is empty"
            max_size_mb = getattr(self, 'max_image_size_mb', 50.0)
            if max_size_mb and max_size_mb > 0:
                limit_bytes = max_size_mb * 1024 * 1024
                if file_size > limit_bytes:
                    return False, (
                        "File too large "
                        f"({file_size / 1024 / 1024:.1f}MB > {max_size_mb:.0f}MB)"
                    )

            # Try to open with PIL to verify it's a valid image
            try:
                with Image.open(image_path) as img:
                    # Verify image can be loaded
                    img.verify()

                # Re-open to check dimensions (verify() closes the file)
                with Image.open(image_path) as img:
                    width, height = img.size

                    # Check for reasonable dimensions
                    if width == 0 or height == 0:
                        return False, "Image has zero dimensions"

                    limit_px = getattr(self, 'max_image_dimension_px', 0)
                    if limit_px and limit_px > 0:
                        if width > limit_px or height > limit_px:
                            return False, (
                                "Image too large "
                                f"({width}x{height} > {limit_px}px limit)"
                            )

            except Exception as e:
                return False, f"Invalid image file: {e}"

            return True, ""

        except Exception as e:
            return False, f"Validation error: {e}"

    def encode_image(self, image_path: Path) -> str:
        """Helper to encode image as base64.

        Args:
            image_path: Path to the image file

        Returns:
            Base64 encoded string of the image
        """
        try:
            with open(image_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise
    
    def get_provider_name(self) -> str:
        """Get the name of this provider.
        
        Returns:
            Provider name string
        """
        return self.__class__.__name__.replace('Provider', '')
    
    def get_info(self) -> Dict[str, Any]:
        """Get provider information.
        
        Returns:
            Dictionary with provider details
        """
        return {
            'provider': self.get_provider_name(),
            'model': self.model_name,
            'api_url': self.api_url,
            'available': self.check_server()
        }
