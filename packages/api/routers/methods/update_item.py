import time
from decimal import Decimal
from fastapi import HTTPException, status
from schemas.datamodel import Item
from schemas.requests_responses import UpdateItemRequest
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from .item_utils import item_table
from .collection_utils import dynamodb_item_to_item


async def update_item(item_id: str, item_request: UpdateItemRequest) -> Item:
    """
    Update a specific Item record by ID.
    """
    print(f'Update request:',str(item_request))
    try:
        # Use UpdateItem for partial updates
        update_expression_parts = []
        expression_attribute_values = {}
        expression_attribute_names = {}  # Needed if attribute names conflict with DynamoDB reserved words

        # Add updated_at timestamp
        current_time = int(time.time())
        update_expression_parts.append("#updated_at = :updated_at")
        expression_attribute_names["#updated_at"] = "updated_at"
        expression_attribute_values[":updated_at"] = current_time

        # Add other fields from the request if they are present
        update_data = item_request.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            # Use ExpressionAttributeNames for potential reserved keywords
            attr_name_placeholder = f"#{key}"
            attr_value_placeholder = f":{key}"
            expression_attribute_names[attr_name_placeholder] = key
            update_expression_parts.append(
                f"{attr_name_placeholder} = {attr_value_placeholder}"
            )

            # Convert float/Decimal to Decimal or int for DynamoDB
            converted_value = value  # Default
            if isinstance(value, float):
                decimal_value = Decimal(str(value))
                converted_value = (
                    int(decimal_value) if decimal_value % 1 == 0 else decimal_value
                )
            elif isinstance(value, Decimal):  # Handle direct Decimal input
                converted_value = int(value) if value % 1 == 0 else value
            elif key in [
                "label_filtering_rules",
                "description_filtering_rules",
            ] and isinstance(value, list):
                converted_rules_list = []
                for rule in value:
                    if isinstance(rule, dict):
                        converted_rule = {}
                        for rule_key, rule_value in rule.items():
                            # Check specific float fields within rules
                            if rule_key in [
                                "min_confidence",
                                "min_image_size_percent",
                            ] and isinstance(rule_value, float):
                                converted_rule[rule_key] = Decimal(str(rule_value))
                            else:
                                converted_rule[rule_key] = rule_value
                        converted_rules_list.append(converted_rule)
                    else:
                        converted_rules_list.append(rule)  # Append non-dict items as is
                # Assign the processed list
                converted_value = converted_rules_list

            expression_attribute_values[attr_value_placeholder] = converted_value

        if not update_expression_parts:
            # If only timestamp is updated, or nothing changed
            if (
                "#updated_at" not in expression_attribute_names
            ):  # No fields provided at all
                # Maybe return current item or raise 400 Bad Request?
                # Let's fetch and return the current item
                response = item_table.get_item(Key={"id": item_id})
                item = response.get("Item")
                if not item:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Item with ID {item_id} not found",
                    )
                return dynamodb_item_to_item(item)

        update_expression = "SET " + ", ".join(update_expression_parts)

        response = item_table.update_item(
            Key={"id": item_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW",  # Return the updated item
            ConditionExpression=Attr("id").exists(),  # Ensure item exists before update
        )

        # The updated item is in response['Attributes']
        return dynamodb_item_to_item(response["Attributes"])

    except ClientError as e:
        print(f"Error updating Item {item_id}: {e}")  # Add logging
        # Safely check error code
        error_code = ""
        if hasattr(e, 'response') and e.response:
            error_info = e.response.get('Error', {})
            error_code = error_info.get('Code', '')
        
        if error_code == "ConditionalCheckFailedException":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with ID {item_id} not found",
            ) from e
        else:
            # Safely access the error message with fallbacks
            error_message = "Unknown error"
            if hasattr(e, 'response') and e.response:
                error_info = e.response.get('Error', {})
                error_message = error_info.get('Message', str(e))
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update Item {item_id}: {error_message}",
            ) from e
    except Exception as e:
        print(f"Unexpected error updating Item {item_id}: {e}")  # Add logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
