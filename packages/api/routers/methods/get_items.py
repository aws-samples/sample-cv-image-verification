from fastapi import HTTPException, status
from schemas.requests_responses import ItemListResponse
from botocore.exceptions import ClientError
from .item_utils import item_table  # Updated import
from .collection_utils import dynamodb_item_to_item  # Updated import


async def get_items() -> ItemListResponse:
    """
    Retrieve a list of all Item records.
    """
    try:
        response = item_table.scan()
        items = [dynamodb_item_to_item(item) for item in response.get("Items", [])]
        # Handle pagination if necessary
        while "LastEvaluatedKey" in response:
            response = item_table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(
                [dynamodb_item_to_item(item) for item in response.get("Items", [])]
            )
        return ItemListResponse(items=items)
    except ClientError as e:
        print(f"Error scanning Item table: {e}")  # Add logging
        error_message = e.response.get('Error', {}).get('Message', str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve Items: {error_message}",
        ) from e
    except Exception as e:
        print(f"Unexpected error retrieving Items: {e}")  # Add logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
