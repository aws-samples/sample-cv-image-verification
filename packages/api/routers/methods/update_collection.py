import time
from decimal import Decimal
from enum import Enum
from typing import cast, Any  # Import cast and Any
from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

# Import necessary models and utils
from .collection_utils import collections_table, dynamodb_item_to_collection
from schemas.requests_responses import UpdateCollectionRequest, UpdateCollectionResponse


async def update_collection(
    collection_id: str, collection_request: UpdateCollectionRequest
) -> UpdateCollectionResponse:
    """
    Implementation to update an existing collection.
    Note: This does not currently support updating the embedded Item instances.
    """
    try:
        update_expression_parts = []
        expression_attribute_values = {}
        expression_attribute_names = {}

        current_time = int(time.time())
        update_expression_parts.append("#updated_at = :updated_at")
        expression_attribute_names["#updated_at"] = "updated_at"
        expression_attribute_values[":updated_at"] = current_time

        # Exclude 'items' and 'files' from direct update via this method for simplicity
        update_data = collection_request.model_dump(
            exclude_unset=True, exclude={"items", "files"}
        )

        for key, value in update_data.items():
            attr_name_placeholder = f"#{key}"
            attr_value_placeholder = f":{key}"
            expression_attribute_names[attr_name_placeholder] = key
            update_expression_parts.append(
                f"{attr_name_placeholder} = {attr_value_placeholder}"
            )

            # Convert value for DynamoDB
            if isinstance(value, float):
                # Convert float to Decimal first for precision
                decimal_value = Decimal(str(value))
                # Convert to int if it's a whole number, else keep as Decimal
                converted_value = (
                    int(decimal_value) if decimal_value % 1 == 0 else decimal_value
                )
            elif isinstance(value, Decimal):  # Handle Decimal input directly
                converted_value = int(value) if value % 1 == 0 else value
            elif isinstance(value, Enum):
                converted_value = value.value
            # Note: Lists (like files) are excluded, so no complex list handling needed here
            else:  # Handles int, str, bool, etc.
                converted_value = value

            # Cast to Any to handle potential mypy inference issues with int/Decimal
            expression_attribute_values[attr_value_placeholder] = cast(
                Any, converted_value
            )

        if (
            not expression_attribute_values or len(expression_attribute_values) == 1
        ):  # Only timestamp updated
            response = collections_table.get_item(Key={"id": collection_id})
            item = response.get("Item")
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
                )
            return UpdateCollectionResponse(collection=dynamodb_item_to_collection(item))

        update_expression = "SET " + ", ".join(update_expression_parts)

        response = collections_table.update_item(
            Key={"id": collection_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW",
            ConditionExpression=Attr("id").exists(),
        )
        return UpdateCollectionResponse(
            collection=dynamodb_item_to_collection(response["Attributes"])
        )

    except ClientError as e:
        print(f"Error updating collection {collection_id}: {e}")
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update collection: {e.response['Error']['Message']}",
            ) from e
    except Exception as e:
        print(f"Unexpected error updating collection {collection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
