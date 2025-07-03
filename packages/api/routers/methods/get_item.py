from fastapi import HTTPException, status
from schemas.datamodel import Item
from botocore.exceptions import ClientError
from .item_utils import item_table
from .collection_utils import dynamodb_item_to_item


async def get_item(item_id: str) -> Item:
    """
    Retrieve a specific Item record by ID.
    """
    try:
        response = item_table.get_item(Key={"id": item_id})
        item = response.get("Item")
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with ID {item_id} not found",
            )
        return dynamodb_item_to_item(item)
    except ClientError as e:
        print(f"Error retrieving Item {item_id}: {e}")  # Add logging
        # Boto3 raises ClientError for various issues, check if it's specifically 'ResourceNotFoundException'
        # Although get_item doesn't raise ResourceNotFoundException, it returns no 'Item'.
        # This generic handling is okay here, but could be more specific if needed.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve Item {item_id}: {e.response['Error']['Message']}",
        ) from e
    except HTTPException as e:  # Re-raise our specific 404
        raise e
    except Exception as e:
        print(f"Unexpected error retrieving Item {item_id}: {e}")  # Add logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
