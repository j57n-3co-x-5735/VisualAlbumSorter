"""MLX VLM vision model provider implementation."""

import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import requests

from .base import VisionModelProvider

logger = logging.getLogger(__name__)


class MLXVLMProvider(VisionModelProvider):
    """Provider for MLX VLM vision models."""
    
    def __init__(self, model_name: str = "mlx-community/Phi-3-vision-128k-instruct-4bit", 
                 api_url: str = "http://127.0.0.1:8000/generate",
                 config: Optional[Dict[str, Any]] = None):
        """Initialize MLX VLM provider.
        
        Args:
            model_name: Name of the MLX model to use
            api_url: MLX VLM API endpoint URL
            config: Optional provider-specific configuration
        """
        super().__init__(model_name, api_url, config)
        self.base_url = api_url.replace('/generate', '')
    
    def classify_image(self, image_path: Path, prompt: str, max_retries: int = 3) -> str:
        """Classify an image using MLX VLM vision model.
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt for the model
            max_retries: Maximum number of retry attempts
            
        Returns:
            The model's response text, or empty string on error
        """
        for attempt in range(max_retries):
            try:
                # MLX VLM expects a file path, not base64
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "image": [str(image_path)],  # Image path must be a string in a list
                    "max_tokens": self.config.get("max_tokens", 100),
                    "stream": False
                }
                
                # Add any extra config parameters
                for key in ["temperature", "top_p"]:
                    if key in self.config:
                        payload[key] = self.config[key]
                
                logger.debug(f"Sending request to MLX VLM (attempt {attempt + 1}/{max_retries})")
                resp = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=60,  # MLX can be slower
                )
                resp.raise_for_status()
                
                # Parse the response
                response_data = resp.json()
                response_text = response_data.get('text', '').strip()
                
                # Clean up any special tokens
                if '<|end|>' in response_text:
                    response_text = response_text.split('<|end|>')[0].strip()
                
                logger.debug(f"MLX VLM response: {response_text}")
                return response_text
                
            except (requests.Timeout, requests.ConnectionError) as e:
                logger.warning(
                    f"MLX VLM network error (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Max retries reached for {image_path}")
                    return ""
                    
            except Exception as e:
                logger.error(f"MLX VLM classification failed: {e}")
                return ""
        
        return ""
    
    def check_server(self) -> bool:
        """Check if MLX VLM server is running.
        
        Returns:
            True if server is available, False otherwise
        """
        try:
            resp = requests.get(self.base_url, timeout=3)
            
            if resp.status_code in [200, 404]:  # Server responds even if endpoint not found
                logger.info("MLX VLM server is running")
                return True
            else:
                logger.warning(f"MLX VLM server returned status {resp.status_code}")
                return False
                
        except requests.ConnectionError:
            logger.error("MLX VLM server not reachable at http://127.0.0.1:8000")
            logger.info("Please start the MLX VLM server:")
            logger.info("  mlx_vlm.server --model mlx-community/Phi-3-vision-128k-instruct-4bit")
            return False
        except Exception as e:
            logger.error(f"Failed to check MLX VLM server: {e}")
            return False