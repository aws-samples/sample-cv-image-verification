#!/usr/bin/env python3
"""
Script to test the LLM configuration functionality.
This script demonstrates how to get and set the system prompt and model ID.
"""

import os
import sys
import logging

# Add the parent directory to the path so we can import from packages/api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_helpers import (
    save_system_prompt,
    save_model_id,
    get_system_prompt,
    get_model_id,
    load_config_history,
    CONFIG_TYPE_SYSTEM_PROMPT,
    CONFIG_TYPE_MODEL_ID,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_system_prompt():
    """Test system prompt configuration"""
    logger.info("Testing system prompt configuration...")

    # Get current system prompt
    current_prompt = get_system_prompt()
    logger.info(f"Current system prompt: {current_prompt[:50]}...")

    # Save a new system prompt
    new_prompt = "This is a test system prompt for testing purposes."
    logger.info(f"Saving new system prompt: {new_prompt}")
    save_system_prompt(new_prompt, "Test system prompt")

    # Verify the new system prompt
    updated_prompt = get_system_prompt()
    logger.info(f"Updated system prompt: {updated_prompt}")
    assert updated_prompt == new_prompt, "System prompt was not updated correctly"

    # Get system prompt history
    history = load_config_history(CONFIG_TYPE_SYSTEM_PROMPT, limit=5)
    logger.info(f"System prompt history (last {len(history)} entries):")
    for item in history:
        logger.info(
            f"  - {item['timestamp']}: {item['value'][:30]}... (active: {item['is_active']})"
        )

    logger.info("System prompt test completed successfully.")


def test_model_id():
    """Test model ID configuration"""
    logger.info("Testing model ID configuration...")

    # Get current model ID
    current_model_id = get_model_id()
    logger.info(f"Current model ID: {current_model_id}")

    # Save a new model ID
    new_model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    logger.info(f"Saving new model ID: {new_model_id}")
    save_model_id(new_model_id, "Test model ID")

    # Verify the new model ID
    updated_model_id = get_model_id()
    logger.info(f"Updated model ID: {updated_model_id}")
    assert updated_model_id == new_model_id, "Model ID was not updated correctly"

    # Get model ID history
    history = load_config_history(CONFIG_TYPE_MODEL_ID, limit=5)
    logger.info(f"Model ID history (last {len(history)} entries):")
    for item in history:
        logger.info(
            f"  - {item['timestamp']}: {item['value']} (active: {item['is_active']})"
        )

    logger.info("Model ID test completed successfully.")


def restore_defaults():
    """Restore default configuration"""
    logger.info("Restoring default configuration...")

    default_prompt = """You task is to find matches for each of the listed items listed below. Each item should have one primary image that is evidence of the item being completed.
Ensure you include a reasoning.
Ensure you take timing into account, i.e. if the image is an "after" photo then ensure the time of the image is indeed after the "before" photo.
                     When the photos are sent through they will be sent as a set, first the ID(s) of the images and then the image the IDs represent. Pay close attention to the coordinate of the image and choose accordingly. When providing the reasoning, include the position of the image itself in the reasoning."""

    default_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    save_system_prompt(default_prompt, "Restored default system prompt")
    save_model_id(default_model_id, "Restored default model ID")

    logger.info("Default configuration restored.")


if __name__ == "__main__":
    try:
        test_system_prompt()
        test_model_id()
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
    finally:
        # Always restore defaults after testing
        restore_defaults()
