import boto3
from decimal import Decimal
from typing import Any, Type, cast
from pydantic import BaseModel
from enum import Enum
from botocore.client import Config

# Import necessary models and constants from the main project structure
from schemas.datamodel import (
    Collection,
    Item,
    CollectionFileStatus,
)
from constants import (
    AWS_REGION,
    COLLECTIONS_TABLE_NAME,
    ITEMS_TABLE_NAME,
    VERIFICATION_JOBS_TABLE_NAME,
)
# Import map utils if they are used by methods extracted here (or keep in methods files)
# from utils.map import get_address_suggestions, get_coordinates_from_address

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
collections_table = dynamodb.Table(COLLECTIONS_TABLE_NAME)
items_table = dynamodb.Table(ITEMS_TABLE_NAME)
verification_jobs_table = dynamodb.Table(VERIFICATION_JOBS_TABLE_NAME)
s3_client = boto3.client("s3", config=Config(signature_version="s3v4"))

# --- Helper Functions for DynamoDB <-> Pydantic Conversion ---


# Helper function to recursively convert Python data structures (dicts, lists, primitives),
# converting floats to Decimals for DynamoDB compatibility.
def _recursive_float_to_decimal(data: Any) -> Any:
    """Recursively traverses data structure, converting floats to Decimals."""
    if isinstance(data, dict):
        return {key: _recursive_float_to_decimal(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_recursive_float_to_decimal(item) for item in data]
    elif isinstance(data, float):
        return Decimal(str(data))
    return data


# Helper function to convert Pydantic model to DynamoDB item (generic)
def model_to_dynamodb_item(model_instance: BaseModel) -> dict[str, Any]:
    """Converts a Pydantic model instance to a DynamoDB-compatible dictionary."""
    item_dict = model_instance.model_dump(
        mode="json", exclude_none=True
    )  # Use exclude_none
    print(item_dict)
    # Cast the result of the recursive helper
    return cast(dict[str, Any], _recursive_float_to_decimal(item_dict))


# Helper function to convert DynamoDB item to a Pydantic model (generic)
def dynamodb_item_to_model(item: dict, model_class: Type[BaseModel]) -> BaseModel:
    """Converts a DynamoDB item to a specific Pydantic model instance."""
    processed_item = {}

    # Recursively convert Decimals back to float/int
    def parse_decimal(value: Any) -> Any:
        if isinstance(value, list):
            return [parse_decimal(v) for v in value]
        elif isinstance(value, dict):
            return {k: parse_decimal(v) for k, v in value.items()}
        elif isinstance(value, Decimal):
            if value % 1 == 0:
                return int(value)
            else:
                return float(value)
        return value

    item = parse_decimal(item)

    # Process fields based on model definition
    for key, value in item.items():
        if key not in model_class.model_fields:
            processed_item[key] = value  # Keep extra fields if any
            continue

        field_info = model_class.model_fields[key]
        annotation = field_info.annotation
        origin_type = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", [])

        # Handle Enums
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            try:
                processed_item[key] = annotation(value)
            except ValueError:
                print(
                    f"Warning: Invalid enum value '{value}' for field '{key}' in {model_class.__name__} {item.get('id')}"
                )
                processed_item[key] = None  # Or default
        # Handle Lists of Pydantic Models
        elif (
            origin_type is list
            and args
            and isinstance(args[0], type)
            and issubclass(args[0], BaseModel)
        ):
            model_in_list = args[0]
            # Ensure value is a list before iterating
            if isinstance(value, list):
                processed_item[key] = [
                    dynamodb_item_to_model(i, model_in_list)
                    for i in value
                    if isinstance(i, dict)
                ]
            else:
                print(
                    f"Warning: Expected list for field '{key}' but got {type(value)}. Setting to empty list."
                )
                processed_item[key] = []
        # Handle simple types or lists of simple types
        else:
            processed_item[key] = value

    # Ensure list fields expected by the model are present
    for field_name, field_info in model_class.model_fields.items():
        origin_type = getattr(field_info.annotation, "__origin__", None)
        if origin_type is list and field_name not in processed_item:
            processed_item[field_name] = []

    try:
        return model_class.model_validate(processed_item)
    except Exception as e:
        print(
            f"Error validating/creating model {model_class.__name__} from item {item.get('id')}: {e}"
        )
        print(f"Processed item data: {processed_item}")
        raise


# Specific helper for Collection
def dynamodb_item_to_collection(item: dict) -> Collection:
    # Need to handle nested CollectionFile status specifically before generic conversion
    if "files" in item and isinstance(item["files"], list):
        for file_data in item["files"]:
            if (
                isinstance(file_data, dict)
                and "status" in file_data
                and isinstance(file_data["status"], str)
            ):
                try:
                    file_data["status"] = CollectionFileStatus(file_data["status"])
                except ValueError:
                    print(
                        f"Warning: Invalid CollectionFileStatus value '{file_data['status']}' for file {file_data.get('id')}"
                    )
                    file_data["status"] = None  # Or default
    # Cast the result to the specific Pydantic model type
    return cast(Collection, dynamodb_item_to_model(item, Collection))


# Specific helper for Item
def dynamodb_item_to_item(item: dict) -> Item:
    # Cast the result to the specific Pydantic model type
    return cast(Item, dynamodb_item_to_model(item, Item))


# Specific helper for Collection to DynamoDB (if needed, otherwise generic is fine)
def collection_to_dynamodb_item(collection: Collection) -> dict:
    return model_to_dynamodb_item(collection)
