import time
import uuid
from fastapi import HTTPException, status
from schemas.datamodel import Item
from schemas.requests_responses import CreateItemRequest
from botocore.exceptions import ClientError
from .item_utils import item_table
from .collection_utils import model_to_dynamodb_item


async def create_item(item_request: CreateItemRequest) -> Item:
    """
    Create a new Item record.
    """
    current_time = int(time.time())
    item_id = str(uuid.uuid4())

    item = Item(
        id=item_id,
        created_at=current_time,
        updated_at=current_time,
        name=item_request.name,
        cluster_number=item_request.cluster_number,
        description=item_request.description,
        label_filtering_rules=item_request.label_filtering_rules or [],
        description_filtering_rules=item_request.description_filtering_rules or [],
        agent_ids=item_request.agent_ids or []
    )

    try:
        item_data = model_to_dynamodb_item(item)  # Use generic model converter
        item_table.put_item(Item=item_data)
        return item
    except ClientError as e:
        print(f"Error creating Item: {e}")  # Add logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Item: {e.response['Error']['Message']}",
        ) from e
    except Exception as e:
        print(f"Unexpected error creating Item: {e}")  # Add logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
