"""LM Studio vision model provider implementation."""

import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import requests

from .base import VisionModelProvider

logger = logging.getLogger(__name__)


class LMStudioProvider(VisionModelProvider):
    """Provider for LM Studio vision models (OpenAI-compatible API)."""
    
    def __init__(self, model_name: str = "qwen2.5-omni-3b", 
                 api_url: str = "http://localhost:1234/v1/chat/completions",
                 config: Optional[Dict[str, Any]] = None):
        """Initialize LM Studio provider.
        
        Args:
            model_name: Name of the model in LM Studio
            api_url: LM Studio API endpoint URL
            config: Optional provider-specific configuration
        """
        super().__init__(model_name, api_url, config)
        self.models_url = api_url.replace('/chat/completions', '/models')
    
    def classify_image(self, image_path: Path, prompt: str, max_retries: int = 3) -> str:
        """Classify an image using LM Studio vision model.

        Args:
            image_path: Path to the image file
            prompt: Text prompt for the model
            max_retries: Maximum number of retry attempts

        Returns:
            The model's response text, or empty string on error
        """
        # Validate image before attempting classification
        is_valid, error_msg = self.validate_image(image_path)
        if not is_valid:
            logger.warning(f"Skipping invalid image {image_path.name}: {error_msg}")
            return ""

        for attempt in range(max_retries):
            try:
                b64_image = self.encode_image(image_path)

                # Simplified OpenAI-compatible payload
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{b64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 100,  # A reasonable limit for a short description
                    "stream": False,
                }

                logger.debug(f"Sending request to LM Studio (attempt {attempt + 1}/{max_retries})")
                resp = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=45,  # Longer timeout for potentially slower models
                )

                # Check for HTTP errors and log response details
                if resp.status_code != 200:
                    error_detail = ""
                    try:
                        error_data = resp.json()
                        error_detail = f": {error_data}"
                    except:
                        error_detail = f": {resp.text[:200]}"

                    logger.error(
                        f"LM Studio returned {resp.status_code} for {image_path.name}{error_detail}"
                    )

                    # Don't retry on 400 errors (bad request) - likely image format issue
                    if resp.status_code == 400:
                        logger.warning(f"Skipping {image_path.name} due to bad request (likely unsupported image)")
                        return ""

                    resp.raise_for_status()

                # Parse the OpenAI-compatible response structure
                response_data = resp.json()
                response_text = (response_data.get("choices", [{}])[0]
                               .get("message", {})
                               .get("content", "")
                               .strip())

                if not response_text:
                    logger.warning(f"LM Studio returned empty response for {image_path}")
                    return ""

                logger.debug(f"LM Studio response: {response_text}")
                return response_text

            except (requests.Timeout, requests.ConnectionError) as e:
                logger.warning(
                    f"LM Studio network error (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"Max retries reached for {image_path}")
                    return ""

            except requests.HTTPError as e:
                logger.error(f"LM Studio HTTP error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                else:
                    return ""

            except Exception as e:
                logger.error(f"LM Studio classification failed: {e}")
                return ""
        
        return ""
    
    def check_server(self) -> bool:
        """Check if LM Studio server is running.
        
        Returns:
            True if server is available, False otherwise
        """
        try:
            # Try to get models list
            resp = requests.get(self.models_url, timeout=5)
            
            if resp.status_code == 200:
                logger.info("LM Studio server is running")
                
                # Try to list available models
                try:
                    models_data = resp.json()
                    model_names = [m.get("id", "") for m in models_data.get("data", [])]
                    if model_names:
                        logger.info(f"Available models: {', '.join(model_names)}")
                except:
                    pass
                
                return True
            else:
                logger.warning(f"LM Studio server returned status {resp.status_code}")
                return False
                
        except requests.ConnectionError:
            logger.error("LM Studio server not reachable at http://localhost:1234")
            logger.info("Please start LM Studio and load a vision model")
            return False
        except Exception as e:
            logger.error(f"Failed to check LM Studio server: {e}")
            return False