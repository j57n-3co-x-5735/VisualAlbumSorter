"""Ollama vision model provider implementation."""

import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import requests

from .base import VisionModelProvider

logger = logging.getLogger(__name__)


class OllamaProvider(VisionModelProvider):
    """Provider for Ollama vision models."""
    
    def __init__(self, model_name: str = "qwen2.5vl:3b", 
                 api_url: str = "http://127.0.0.1:11434/api/generate",
                 config: Optional[Dict[str, Any]] = None):
        """Initialize Ollama provider.
        
        Args:
            model_name: Name of the Ollama model to use
            api_url: Ollama API endpoint URL
            config: Optional provider-specific configuration
        """
        super().__init__(model_name, api_url, config)
        self.tags_url = api_url.replace('/api/generate', '/api/tags')
    
    def classify_image(self, image_path: Path, prompt: str, max_retries: int = 3) -> str:
        """Classify an image using Ollama vision model.
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt for the model
            max_retries: Maximum number of retry attempts
            
        Returns:
            The model's response text, or empty string on error
        """
        for attempt in range(max_retries):
            try:
                b64_image = self.encode_image(image_path)
                
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "images": [b64_image],
                    "stream": False,
                }
                
                # Add any extra config parameters
                if self.config:
                    payload.update(self.config)
                
                logger.debug(f"Sending request to Ollama (attempt {attempt + 1}/{max_retries})")
                resp = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=30,
                )
                resp.raise_for_status()
                
                response_text = resp.json().get("response", "").strip()
                logger.debug(f"Ollama response: {response_text}")
                return response_text
                
            except (requests.Timeout, requests.ConnectionError) as e:
                logger.warning(
                    f"Ollama network error (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Max retries reached for {image_path}")
                    return ""
                    
            except Exception as e:
                logger.error(f"Ollama classification failed: {e}")
                return ""
        
        return ""
    
    def check_server(self) -> bool:
        """Check if Ollama server is running and model is available.
        
        Returns:
            True if server and model are available, False otherwise
        """
        try:
            resp = requests.get(self.tags_url, timeout=5)
            resp.raise_for_status()
            
            models = {m["name"] for m in resp.json().get("models", [])}
            
            if self.model_name not in models:
                logger.warning(
                    f"Model {self.model_name} not found. "
                    f"Available models: {', '.join(models)}"
                )
                logger.info(f"Run: ollama pull {self.model_name}")
                return False
                
            logger.info(f"Ollama server is running with model {self.model_name}")
            return True
            
        except requests.ConnectionError:
            logger.error("Ollama server not reachable. Start with: ollama serve")
            return False
        except Exception as e:
            logger.error(f"Failed to check Ollama server: {e}")
            return False