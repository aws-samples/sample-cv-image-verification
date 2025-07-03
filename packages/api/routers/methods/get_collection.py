from fastapi import HTTPException, status
from botocore.exceptions import ClientError

# Import necessary models and utils
from .collection_utils import collections_table, dynamodb_item_to_collection
from schemas.requests_responses import CollectionResponse


async def get_collection(collection_id: str) -> CollectionResponse:
    """
    Implementation to retrieve a specific collection by its ID.
    """
    try:
        response = collections_table.get_item(Key={"id": collection_id})
        item = response.get("Item")
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
            )
        return CollectionResponse(collection=dynamodb_item_to_collection(item))
    except ClientError as e:
        print(f"Error retrieving collection {collection_id}: {e}")
        error_message = "Unknown error"
        if hasattr(e, 'response') and e.response:
            error_dict = e.response.get('Error', {})
            error_message = error_dict.get('Message', str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve collection: {error_message}",
        ) from e
    except HTTPException as e:  # Re-raise our 404
        raise e
    except Exception as e:
        print(f"Unexpected error retrieving collection {collection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
