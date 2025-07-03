import time
from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

# Import necessary models and utils
from .collection_utils import (
    collections_table,
    s3_client,
    dynamodb_item_to_collection,
    model_to_dynamodb_item,
)
from constants import STORAGE_BUCKET_NAME  # Import constant directly
from schemas.datamodel import CollectionFile
from schemas.requests_responses import AddFileRequest, AddFileResponse


async def add_file_to_collection(
    collection_id: str, file_data: AddFileRequest
) -> AddFileResponse:
    """
    Implementation to add a file to a collection after it has been uploaded to S3.
    """
    current_time = int(time.time())
    file_size = None

    # Fetch file size from S3
    if file_data.s3_key:
        try:
            head_response = s3_client.head_object(
                Bucket=STORAGE_BUCKET_NAME, Key=file_data.s3_key
            )
            file_size = head_response.get("ContentLength")
        except ClientError as e:
            print(
                f"Warning: Could not retrieve metadata for S3 key {file_data.s3_key} when adding file to Collection {collection_id}. Error: {e}"
            )
        except Exception as e:
            print(
                f"Warning: Unexpected error retrieving metadata for S3 key {file_data.s3_key} for Collection {collection_id}. Error: {e}"
            )
    else:
        print(
            f"Warning: No s3_key provided in AddFileRequest for Collection {collection_id}. Cannot fetch size."
        )

    # Create CollectionFile object
    collection_file = CollectionFile(**file_data.model_dump(), size=file_size)
    new_file_item = model_to_dynamodb_item(collection_file)

    try:
        # Update DynamoDB item
        response = collections_table.update_item(
            Key={"id": collection_id},
            UpdateExpression="SET #files = list_append(if_not_exists(#files, :empty_list), :new_file), #updated_at = :updated_at",
            ExpressionAttributeNames={"#files": "files", "#updated_at": "updated_at"},
            ExpressionAttributeValues={
                ":new_file": [new_file_item],
                ":empty_list": [],
                ":updated_at": current_time,
            },
            ReturnValues="ALL_NEW",
            ConditionExpression=Attr("id").exists(),
        )
        updated_collection = dynamodb_item_to_collection(response["Attributes"])
        return AddFileResponse(collection=updated_collection)

    except ClientError as e:
        print(f"Error adding file to collection {collection_id}: {e}")
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to add file to collection: {e.response['Error']['Message']}",
            ) from e
    except Exception as e:
        print(f"Unexpected error adding file to collection {collection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
