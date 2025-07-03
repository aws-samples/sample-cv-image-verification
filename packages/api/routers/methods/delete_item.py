from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from .item_utils import item_table, verification_job_table
from constants import VERIFICATION_JOBS_TABLE_NAME  # Import constant directly


async def delete_item(item_id: str) -> None:
    """
    Delete a specific Item record by ID.
    Prevents deletion if the Item is associated with any Verification Job.
    """
    try:
        # Check if any VerificationJob uses this Item
        paginator = verification_job_table.meta.client.get_paginator("scan")
        scan_kwargs = {
            "TableName": VERIFICATION_JOBS_TABLE_NAME,
            "ProjectionExpression": "id, items",  # Only fetch necessary fields
            "FilterExpression": "attribute_exists(items)",  # Optimization: only scan items that have items
        }

        item_in_use = False
        for page in paginator.paginate(**scan_kwargs):
            for item in page.get("Items", []):
                # The 'items' attribute in DynamoDB is a list of maps (dictionaries)
                item_instances = item.get("items", [])
                if isinstance(item_instances, list):
                    for item_instance_data in item_instances:
                        # Ensure it's a dictionary and has 'item_id'
                        if (
                            isinstance(item_instance_data, dict)
                            and item_instance_data.get("item_id") == item_id
                        ):
                            item_in_use = True
                            break  # Found one, no need to check further in this item
                if item_in_use:
                    break  # Found one, no need to check further pages
            if item_in_use:
                break  # Exit outer loop as well

        if item_in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete Item {item_id}: It is currently associated with one or more verification jobs.",
            )

        # If not in use, proceed with deletion
        item_table.delete_item(
            Key={"id": item_id},
            ConditionExpression=Attr("id").exists(),  # Ensure item exists before delete
        )
        # No return needed for 204
    except ClientError as e:
        print(f"Error deleting Item {item_id}: {e}")  # Add logging
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # Item did not exist
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with ID {item_id} not found",
            ) from e
        else:
            # Other DynamoDB error
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete Item {item_id}: {e.response['Error']['Message']}",
            ) from e
    except Exception as e:
        print(f"Unexpected error deleting Item {item_id}: {e}")  # Add logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
