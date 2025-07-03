import uuid
import time
from fastapi import HTTPException, status
from botocore.exceptions import ClientError

# Import necessary models and utils
from .collection_utils import (
    collections_table,
    items_table,
    dynamodb_item_to_item,
    collection_to_dynamodb_item,
)
from schemas.datamodel import Collection
from schemas.requests_responses import CreateCollectionRequest, CreateCollectionResponse


async def create_collection(
    collection_request: CreateCollectionRequest,
) -> CreateCollectionResponse:
    """
    Implementation to create a new collection, including associated Item instances based on item_ids.
    """
    current_time = int(time.time())
    collection_id = str(uuid.uuid4())
    fetched_items = []
    
    if not collection_request.item_ids or len(collection_request.item_ids) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one Item ID must be provided in the request.",
        )

    if collection_request.item_ids:
        for item_id in collection_request.item_ids:
            try:
                item_response = items_table.get_item(Key={"id": item_id})
                item_item = item_response.get("Item")
                if not item_item:
                    print(
                        f"Warning: Item with ID {item_id} not found. Skipping for Collection {collection_id}."
                    )
                    continue

                item_data = dynamodb_item_to_item(item_item)
                fetched_items.append(item_data)

            except ClientError as e:
                print(f"Error fetching Item {item_id} for Collection {collection_id}: {e}")
                error_message = "Unknown error"
                if hasattr(e, 'response') and e.response and 'Error' in e.response:
                    error_message = e.response['Error'].get('Message', 'Unknown error')
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to fetch Item details for ID {item_id}: {error_message}",
                ) from e
            except Exception as e:
                print(
                    f"Error processing Item {item_id} for Collection {collection_id}: {e}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to process Item details for ID {item_id}: {str(e)}",
                ) from e

    collection = Collection(
        id=collection_id,
        created_at=current_time,
        updated_at=current_time,
        description=collection_request.description,
        files=collection_request.files or [],
        items=fetched_items,
        address=collection_request.address,
    )

    try:
        item_data = collection_to_dynamodb_item(collection)
        collections_table.put_item(Item=item_data)
        return CreateCollectionResponse(collection=collection)
    except ClientError as e:
        print(f"Error creating collection in DynamoDB: {e}")
        error_message = "Unknown error"
        if hasattr(e, 'response') and e.response and 'Error' in e.response:
            error_message = e.response['Error'].get('Message', 'Unknown error')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save collection: {error_message}",
        ) from e
    except Exception as e:
        print(f"Unexpected error creating collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during collection creation: {str(e)}",
        ) from e
