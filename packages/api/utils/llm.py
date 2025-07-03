import boto3
import time
from langchain_aws import ChatBedrockConverse
from typing import Optional
from constants import get_bedrock_role_arn
from utils.config_helpers import get_model_id

_bedrock_runtime_client = None
_bedrock_client_timestamp = None


def get_model():
    """Returns a configured ChatBedrockConverse model instance."""
    sync_client = get_bedrock_runtime()
    model_id = get_model_id()
    return ChatBedrockConverse(
        client=sync_client, model=model_id, temperature=0.1, max_tokens=8000
    )


def create_system_message(message: str):
    """Creates appropriate system message format based on model type."""
    model_id = get_model_id()

    if "nova" in model_id:
        return {
            "role": "user",
            "content": message,
        }
    elif "claude" in model_id:
        return {
            "role": "system",
            "content": message,
        }


def calculate_llm_pricing(
    input_tokens: Optional[int] = 0,
    output_tokens: Optional[int] = 0,
    model_id: Optional[str] = None,
) -> float:
    """Calculate the pricing for input and output tokens based on the model's pricing."""
    if model_id is None:
        model_id = get_model_id()

    # Default to Claude 3.5 Sonnet pricing
    input_price_per_1k = 0.003
    output_price_per_1k = 0.015

    # Set pricing based on model ID
    if "amazon.nova-micro" in model_id:
        input_price_per_1k = 0.000037
        output_price_per_1k = 0.00000925
    elif "amazon.nova-lite" in model_id:
        input_price_per_1k = 0.000063
        output_price_per_1k = 0.00001575
    elif "amazon.nova-pro" in model_id:
        input_price_per_1k = 0.00084
        output_price_per_1k = 0.00021
    elif "claude-3-7-sonnet" in model_id:
        input_price_per_1k = 0.003
        output_price_per_1k = 0.015
    elif "claude-3-5-sonnet" in model_id:
        input_price_per_1k = 0.003
        output_price_per_1k = 0.015
    elif "claude-3-5-haiku" in model_id:
        input_price_per_1k = 0.0008
        output_price_per_1k = 0.004

    total_cost = (input_tokens or 0) * input_price_per_1k / 1000 + (
        output_tokens or 0
    ) * output_price_per_1k / 1000

    return total_cost


def get_bedrock_runtime():
    """Creates and returns a cached Bedrock runtime client with credentials from an assumed role."""
    global _bedrock_runtime_client, _bedrock_client_timestamp
    
    current_time = time.time()
    
    # Check if client needs to be refreshed (older than 3000 seconds)
    if _bedrock_runtime_client and _bedrock_client_timestamp:
        if current_time - _bedrock_client_timestamp >= 3000:
            _bedrock_runtime_client = None
            _bedrock_client_timestamp = None
    
    if _bedrock_runtime_client:
        return _bedrock_runtime_client

    session = boto3.session.Session()

    _bedrock_runtime_client = session.client("bedrock-runtime")
    
    bedrock_role_arn = get_bedrock_role_arn()

    if bedrock_role_arn:
        sts_client = session.client("sts")

        response = sts_client.assume_role(
            RoleArn=bedrock_role_arn,
            RoleSessionName="BedrockSession",
            DurationSeconds=3600,
        )
        credentials = response["Credentials"]

        _bedrock_runtime_client = session.client(
            "bedrock-runtime",
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
        _bedrock_client_timestamp = current_time
    else:
        # If no role ARN is provided, use the default client
        if _bedrock_runtime_client:
            # If the client is already initialized, return it
            return _bedrock_runtime_client
        else:
            # If the client is not initialized, initialize it
            _bedrock_runtime_client = session.client("bedrock-runtime")
            _bedrock_client_timestamp = current_time
            
    return _bedrock_runtime_client
