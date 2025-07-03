import uuid
import time
from fastapi import HTTPException, status
from botocore.exceptions import ClientError

# Import necessary models and utils
from .collection_utils import collections_table, s3_client
from constants import STORAGE_BUCKET_NAME  # Import constant directly
from schemas.requests_responses import PresignUploadResponse


async def presign_collection_file_upload(
    collection_id: str, content_type: str, filename: str
) -> PresignUploadResponse:
    """
    Implementation to generate a presigned URL for uploading a file to S3 for a specific collection.
    """
    # Validate that the collection exists
    try:
        response = collections_table.get_item(
            Key={"id": collection_id}, ProjectionExpression="id"
        )
        if "Item" not in response:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
            )
    except ClientError as e:
        print(f"Error checking collection existence {collection_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking collection existence",
        ) from e

    # Generate file ID and S3 key
    file_id = str(uuid.uuid4())
    s3_key = f"collections/{collection_id}/files/{file_id}/{filename}"
    current_time = int(time.time())

    try:
        # Generate presigned URL for PUT
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": STORAGE_BUCKET_NAME,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=3600,  # 1 hour
        )

        return PresignUploadResponse(
            presigned_url=presigned_url,
            file_metadata={
                "id": file_id,
                "created_at": current_time,
                "s3_key": s3_key,
                "content_type": content_type,
                "filename": filename,
                # Size will be added later by add_file_to_collection
            },
        )
    except ClientError as e:
        print(
            f"Error generating presigned URL for collection {collection_id}, file {filename}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {e.response['Error']['Message']}",
        ) from e
    except Exception as e:
        print(
            f"Unexpected error generating presigned URL for collection {collection_id}, file {filename}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
