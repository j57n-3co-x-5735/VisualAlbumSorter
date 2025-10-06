"""Image classification logic with configurable rules."""

import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ..providers.base import VisionModelProvider

logger = logging.getLogger(__name__)


class ImageClassifier:
    """Handles image classification based on configurable rules."""
    
    def __init__(self, provider: VisionModelProvider, task_config: Dict[str, Any]):
        """Initialize classifier.
        
        Args:
            provider: Vision model provider instance
            task_config: Task configuration including prompt and rules
        """
        self.provider = provider
        self.prompt = task_config['prompt']
        self.rules = task_config['classification_rules']
        self.task_name = task_config.get('name', 'Unknown Task')
        
        logger.info(f"Initialized classifier for task: {self.task_name}")
    
    def classify(self, image_path: Path, max_retries: int = 3) -> str:
        """Classify an image based on configured rules.
        
        Args:
            image_path: Path to the image file
            max_retries: Maximum number of retry attempts
            
        Returns:
            Classification result: "yes", "no", or "error"
        """
        # Get model response
        response = self.provider.classify_image(image_path, self.prompt, max_retries)
        
        if not response:
            logger.warning(f"Empty response for {image_path}")
            return "error"
        
        # Apply classification rules
        result = self._apply_rules(response)
        
        logger.debug(f"Classification for {image_path}: {result}")
        return result
    
    def _apply_rules(self, response: str) -> str:
        """Apply classification rules to model response.
        
        Args:
            response: Model's response text
            
        Returns:
            "yes" if rules match, "no" otherwise
        """
        rules_type = self.rules.get('type', 'regex_match')
        
        if rules_type == 'regex_match':
            return self._apply_regex_rules(response)
        elif rules_type == 'keyword_match':
            return self._apply_keyword_rules(response)
        elif rules_type == 'custom':
            return self._apply_custom_rules(response)
        elif rules_type == 'always_yes':
            return "yes"
        elif rules_type == 'always_no':
            return "no"
        else:
            logger.warning(f"Unknown rules type: {rules_type}")
            return "no"
    
    def _apply_regex_rules(self, response: str) -> str:
        """Apply regex-based classification rules.
        
        Args:
            response: Model's response text
            
        Returns:
            "yes" if rules match, "no" otherwise
        """
        normalized = self._normalize_text(response)
        rules = self.rules.get('rules', [])
        match_all = self.rules.get('match_all', True)
        
        matches = []
        for rule in rules:
            pattern = rule.get('pattern', '')
            field = rule.get('field', 'response')
            
            text_to_check = normalized if field == 'normalized_response' else response
            
            if pattern:
                match = bool(re.search(pattern, text_to_check, re.IGNORECASE))
                matches.append(match)
                
                rule_name = rule.get('name', pattern[:20])
                logger.debug(f"Rule '{rule_name}': {'matched' if match else 'no match'}")
        
        if not matches:
            return "no"
        
        if match_all:
            return "yes" if all(matches) else "no"
        else:
            return "yes" if any(matches) else "no"
    
    def _apply_keyword_rules(self, response: str) -> str:
        """Apply keyword-based classification rules.
        
        Args:
            response: Model's response text
            
        Returns:
            "yes" if keywords match, "no" otherwise
        """
        normalized = self._normalize_text(response)
        keywords = self.rules.get('keywords', [])
        match_all = self.rules.get('match_all', True)
        
        if not keywords:
            return "no"
        
        matches = [keyword.lower() in normalized for keyword in keywords]
        
        if match_all:
            return "yes" if all(matches) else "no"
        else:
            return "yes" if any(matches) else "no"
    
    def _apply_custom_rules(self, response: str) -> str:
        """Apply custom classification rules.
        
        This is a placeholder for custom rule implementation.
        Users can extend this method for specific needs.
        
        Args:
            response: Model's response text
            
        Returns:
            Classification result
        """
        logger.warning("Custom rules not implemented, returning 'no'")
        return "no"
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for rule matching.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Remove special tokens
        if '<|end|>' in text:
            text = text.split('<|end|>')[0]
        
        # Convert to lowercase
        text = text.lower()
        
        # Replace various dashes with spaces
        text = text.replace("‑", " ").replace("–", " ").replace("-", " ")
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def get_stats(self) -> Dict[str, Any]:
        """Get classifier statistics.
        
        Returns:
            Dictionary with classifier information
        """
        return {
            'task': self.task_name,
            'prompt': self.prompt[:50] + '...' if len(self.prompt) > 50 else self.prompt,
            'rules_type': self.rules.get('type', 'unknown'),
            'num_rules': len(self.rules.get('rules', [])) if 'rules' in self.rules else 0,
            'provider': self.provider.get_provider_name()
        }