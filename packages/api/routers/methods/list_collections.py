from fastapi import HTTPException, status
from typing import Optional
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

# Import necessary models and utils
from .collection_utils import collections_table, dynamodb_item_to_collection
from schemas.datamodel import AssessmentStatus
from schemas.requests_responses import CollectionsListResponse


async def list_collections(
    filter_status: Optional[AssessmentStatus] = None,
) -> CollectionsListResponse:
    """
    Implementation to retrieve a list of all collections, with optional filtering by status.
    """
    try:
        scan_kwargs = {}
        if filter_status:
            scan_kwargs["FilterExpression"] = Attr("status").eq(filter_status.value)

        response = collections_table.scan(**scan_kwargs)
        items = [
            dynamodb_item_to_collection(item) for item in response.get("Items", [])
        ]

        # Handle pagination
        while "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = collections_table.scan(**scan_kwargs)
            items.extend(
                [
                    dynamodb_item_to_collection(item)
                    for item in response.get("Items", [])
                ]
            )

        return CollectionsListResponse(items=items)
    except ClientError as e:
        print(f"Error listing collections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve collections: {e.response['Error']['Message']}",
        ) from e
    except Exception as e:
        print(f"Unexpected error listing collections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
