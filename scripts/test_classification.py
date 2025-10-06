#!/usr/bin/env python3
"""
Test image classification with configured provider and rules.

This script allows testing the Visual Album Sorter classification logic on a single image without processing the entire library.
"""

import sys
import json
import logging
from pathlib import Path
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from visualalbumsorter.core import load_config, ImageClassifier
from visualalbumsorter.utils import create_provider

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_image(image_path: Path, config_path: Path = None, verbose: bool = False):
    """Test classification on a single image.
    
    Args:
        image_path: Path to the image to test
        config_path: Optional path to configuration file
        verbose: Enable verbose output
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check image exists
    if not image_path.exists():
        logger.error(f"Image not found: {image_path}")
        return 1
    
    logger.info(f"Testing image: {image_path}")
    
    try:
        # Load configuration
        config = load_config(config_path)
        logger.info(f"Using configuration for task: {config.task.name}")
        
        # Create provider
        logger.info(f"Initializing {config.provider.type} provider...")
        provider = create_provider(config.provider.__dict__)
        
        # Create classifier
        classifier = ImageClassifier(provider, config.task.__dict__)
        
        # Get raw response
        logger.info(f"Sending prompt: {config.task.prompt}")
        response = provider.classify_image(image_path, config.task.prompt)
        
        if not response:
            logger.error("No response from model")
            return 1
        
        logger.info("\n" + "=" * 60)
        logger.info("MODEL RESPONSE:")
        logger.info("-" * 60)
        print(response)
        logger.info("=" * 60)
        
        # Apply classification rules
        result = classifier.classify(image_path)
        
        # Show rule evaluation details
        if config.task.classification_rules.get('type') == 'regex_match':
            logger.info("\nRULE EVALUATION:")
            logger.info("-" * 60)
            
            normalized = classifier._normalize_text(response)
            logger.debug(f"Normalized text: {normalized}")
            
            for rule in config.task.classification_rules.get('rules', []):
                import re
                pattern = rule.get('pattern', '')
                name = rule.get('name', pattern[:30])
                field = rule.get('field', 'response')
                
                text_to_check = normalized if field == 'normalized_response' else response
                match = bool(re.search(pattern, text_to_check, re.IGNORECASE))
                
                status = "✓ MATCH" if match else "✗ NO MATCH"
                logger.info(f"  {name:20} {status}")
        
        logger.info("-" * 60)
        logger.info(f"\nFINAL RESULT: {result.upper()}")
        
        if result == "yes":
            logger.info("✓ This image WOULD BE ADDED to the album")
        elif result == "no":
            logger.info("✗ This image would NOT be added to the album")
        else:
            logger.error("⚠ Error during classification")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during testing: {e}", exc_info=verbose)
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Test image classification on a single image'
    )
    
    parser.add_argument(
        'image',
        type=Path,
        help='Path to the image to test'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=Path,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Expand user path
    image_path = args.image.expanduser()
    
    return test_image(image_path, args.config, args.verbose)


if __name__ == "__main__":
    sys.exit(main())