#!/usr/bin/env python3
"""
Script to initialize the LLM configuration in DynamoDB.
This script sets up the default system prompt and model ID.
"""

import os
import sys
import argparse
import logging

# Add the parent directory to the path so we can import from packages/api
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_helpers import (
    save_system_prompt,
    save_model_id,
    get_system_prompt,
    get_model_id,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_llm_config(force=False):
    """
    Initialize the LLM configuration with default values.

    Args:
        force: If True, overwrite existing configuration even if it exists
    """
    # Check if system prompt already exists
    current_prompt = get_system_prompt()
    default_prompt = """You task is to find matches for each of the listed items listed below. Each item should have one primary image that is evidence of the item being completed.
Ensure you include a reasoning.
Ensure you take timing into account, i.e. if the image is an "after" photo then ensure the time of the image is indeed after the "before" photo.
                     When the photos are sent through they will be sent as a set, first the ID(s) of the images and then the image the IDs represent. Pay close attention to the coordinate of the image and choose accordingly. When providing the reasoning, include the position of the image itself in the reasoning."""

    if force or current_prompt == default_prompt:
        logger.info("Initializing system prompt...")
        save_system_prompt(default_prompt, "Initial system prompt configuration")
        logger.info("System prompt initialized.")
    else:
        logger.info("System prompt already exists. Use --force to overwrite.")

    # Check if model ID already exists
    current_model_id = get_model_id()
    default_model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    if force or current_model_id == default_model_id:
        logger.info("Initializing model ID...")
        save_model_id(default_model_id, "Initial model ID configuration")
        logger.info("Model ID initialized.")
    else:
        logger.info("Model ID already exists. Use --force to overwrite.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize LLM configuration")
    parser.add_argument(
        "--force", action="store_true", help="Force overwrite of existing configuration"
    )

    args = parser.parse_args()

    init_llm_config(args.force)
