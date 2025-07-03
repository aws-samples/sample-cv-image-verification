import boto3
import time
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from constants import LLM_CONFIG_TABLE_NAME

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CONFIG_TYPE_SYSTEM_PROMPT = "system_prompt"
CONFIG_TYPE_MODEL_ID = "model_id"
VERIFICATION_JOB_SECOND_PASS = "verification_second_pass"

dynamodb = boto3.resource("dynamodb")


def get_config_table():
    """Returns the DynamoDB table for LLM configuration."""
    return dynamodb.Table(LLM_CONFIG_TABLE_NAME)


def save_config(
    config_type: str, value: str, description: Optional[str] = None
) -> Dict[str, Any]:
    """Save a configuration value to DynamoDB."""
    table = get_config_table()
    timestamp = int(time.time())

    item = {
        "config_type": config_type,
        "timestamp": timestamp,
        "value": value,
        "created_at": datetime.utcnow().isoformat(),
        "is_active": "true",
    }

    if description:
        item["description"] = description

    try:
        existing_active = load_active_config(config_type)
        if existing_active:
            table.update_item(
                Key={
                    "config_type": config_type,
                    "timestamp": existing_active["timestamp"],
                },
                UpdateExpression="SET is_active = :active",
                ExpressionAttributeValues={":active": "false"},
            )
    except Exception as e:
        logger.warning(f"Error deactivating existing config: {e}")

    table.put_item(Item=item)
    return item


def load_active_config(config_type: str):
    """Load the currently active configuration of the specified type."""
    table = get_config_table()

    response = table.query(
        KeyConditionExpression="config_type = :type",
        FilterExpression="is_active = :active",
        ExpressionAttributeValues={
            ":type": config_type,
            ":active": "true",
        },
    )

    items = response.get("Items", [])
    if items:
        return items[0]

    return None


def load_config_history(config_type: str, limit: int = 10):
    """Load the history of configurations for the specified type."""
    table = get_config_table()

    response = table.query(
        KeyConditionExpression="config_type = :type",
        ExpressionAttributeValues={":type": config_type},
        ScanIndexForward=False,
        Limit=limit,
    )

    return response.get("Items", [])


def get_second_pass_verification_system_prompt():
    return """Your task is to find if a set of images matches a provided item.
You will be provided with a item Id and a description of the item.
Ensure you include a reasoning. You must consider every criteria and detail in the description, and only give a positive match if ALL the criteria match.
The reasoning should be a short paragraph explaining why the images are a match for the description."""


def get_system_prompt():
    """Get the active system prompt configuration."""
    config = load_active_config(CONFIG_TYPE_SYSTEM_PROMPT)
    if config and "value" in config:
        return str(config["value"])

    return """Your task is to find matches for each of the listed items listed below. Each item should have one primary image that is evidence of the item being completed.
Ensure you include a reasoning. You must consider every criteria and only match the item to the image if ALL the criteria are met. The reasoning should be a short paragraph explaining why the image is a match for the item.
Ensure you take timing into account, i.e. if the image is an "after" photo then ensure the time of the image is indeed after the "before" photo.
When the photos are sent through they will be sent as a set, first the ID(s) of the images and then the image the IDs represent. Pay close attention to the coordinate of the image and choose accordingly. When providing the reasoning, include the position of the image itself in the reasoning.
Each image can contain one or more photos. Each photo is separated by a background filled with a thatched pattern and a border, and photos are placed with space between them to ensure they're clearly distinguished."""


def get_model_id():
    """Get the active model ID configuration."""
    config = load_active_config(CONFIG_TYPE_MODEL_ID)
    if config and "value" in config:
        return str(config["value"])

    return "anthropic.claude-3-5-sonnet-20241022-v2:0"


def save_system_prompt(prompt: str, description: Optional[str] = None):
    """Save a new system prompt configuration."""
    return save_config(CONFIG_TYPE_SYSTEM_PROMPT, prompt, description)


def save_model_id(model_id: str, description: Optional[str] = None):
    """Save a new model ID configuration."""
    return save_config(CONFIG_TYPE_MODEL_ID, model_id, description)


def get_verification_job_second_pass() -> bool:
    """
    Returns a boolean indicating whether a second pass verification should be performed on images.

    This function retrieves the VERIFICATION_JOB_SECOND_PASS configuration value
    which determines if a second verification pass should be executed on images
    to help reduce false positives in image verification.

    Returns:
        bool: True if second pass verification is enabled, False otherwise.
              Returns False if the configuration is not found or invalid.
    """
    """The verification job second pass config value determines if a second pass to verify images should be performed. This helps to prevent false positives."""
    config = load_active_config(VERIFICATION_JOB_SECOND_PASS)
    if config and "value" in config:
        if str(config["value"]).lower() == "true":
            return True

        return False
    else:
        return False


def save_verification_job_second_pass(
    second_pass: str, description: Optional[str] = None
):
    """
    Save a new verification job second pass configuration.

    Args:
        second_pass (bool): True if second pass verification is enabled, False otherwise.
        description (str, optional): A description of the configuration.
    """
    return save_config(VERIFICATION_JOB_SECOND_PASS, second_pass.lower(), description)
