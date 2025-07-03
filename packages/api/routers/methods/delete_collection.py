from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

# Import necessary models and utils
from .collection_utils import collections_table, verification_jobs_table, s3_client
from constants import STORAGE_BUCKET_NAME  # Import constant directly


async def delete_collection(collection_id: str) -> None:
    """
    Implementation to delete a collection after checking for associated verification jobs and deleting S3 files.
    """
    try:
        # 1. Check for associated verification jobs
        verification_query_response = verification_jobs_table.query(
            IndexName="CollectionIdIndex",  # Assumed GSI name
            KeyConditionExpression=Key("collection_id").eq(collection_id),
            Select="COUNT",
        )

        if verification_query_response.get("Count", 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete collection: Associated verification jobs exist.",
            )

        # 2. Get S3 keys for files to delete
        response = collections_table.get_item(
            Key={"id": collection_id}, ProjectionExpression="files"
        )
        item = response.get("Item")
        objects_to_delete = []
        if item and "files" in item:
            files_to_delete = item.get("files", [])
            if isinstance(files_to_delete, list):
                objects_to_delete = [
                    {"Key": file_info["s3_key"]}
                    for file_info in files_to_delete
                    if isinstance(file_info, dict) and "s3_key" in file_info
                ]
            else:
                print(
                    f"Warning: 'files' attribute for collection {collection_id} is not a list: {item.get('files')}"
                )

        # 3. Delete S3 files if any exist
        if objects_to_delete:
            print(
                f"Attempting to delete {len(objects_to_delete)} S3 objects for collection {collection_id}."
            )
            try:
                delete_response = s3_client.delete_objects(
                    Bucket=STORAGE_BUCKET_NAME,
                    Delete={"Objects": objects_to_delete, "Quiet": True},
                )
                if "Errors" in delete_response and delete_response["Errors"]:
                    print(
                        f"Errors deleting S3 objects for collection {collection_id}: {delete_response['Errors']}"
                    )
                    # Log and continue with DynamoDB deletion
            except ClientError as s3_error:
                print(
                    f"Error during S3 batch delete for collection {collection_id}: {s3_error}"
                )
                # Log and continue with DynamoDB deletion

        # 4. Delete the DynamoDB item
        collections_table.delete_item(
            Key={"id": collection_id},
            ConditionExpression=Attr("id").exists(),  # Ensure item exists
        )
        # No return needed for 204

    except ClientError as e:
        print(f"Error deleting collection {collection_id}: {e}")
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # This means the item didn't exist when delete_item was called
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
            ) from e
        elif e.response["Error"]["Code"] == "ResourceNotFoundException":
            # This might happen if the GSI 'CollectionIdIndex' doesn't exist
            print(f"Error querying verification jobs GSI: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error checking for associated jobs (index missing?).",
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete collection: {e.response['Error']['Message']}",
            ) from e
    except HTTPException as e:  # Re-raise our 400
        raise e
    except Exception as e:
        print(f"Unexpected error deleting collection {collection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
