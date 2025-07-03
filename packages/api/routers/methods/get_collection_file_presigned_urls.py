from fastapi import HTTPException, status
from typing import Dict
from botocore.exceptions import ClientError

# Import necessary models and utils
from .collection_utils import collections_table, s3_client
from constants import STORAGE_BUCKET_NAME  # Import constant directly
from schemas.requests_responses import CollectionFilePresignedUrlsResponse


async def get_collection_file_presigned_urls(
    collection_id: str,
) -> CollectionFilePresignedUrlsResponse:
    """
    Implementation to retrieve presigned GET URLs for all files associated with a specific collection.
    """
    try:
        response = collections_table.get_item(
            Key={"id": collection_id}, ProjectionExpression="id, files"
        )
        item = response.get("Item")
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found"
            )

        collection_files = item.get("files", [])
        if not isinstance(collection_files, list):
            print(
                f"Warning: 'files' attribute for collection {collection_id} is not a list: {collection_files}"
            )
            collection_files = []

        presigned_urls: Dict[str, str] = {}
        for file_info_dict in collection_files:
            if (
                not isinstance(file_info_dict, dict)
                or "id" not in file_info_dict
                or "s3_key" not in file_info_dict
            ):
                print(
                    f"Warning: Skipping invalid file data in collection {collection_id}: {file_info_dict}"
                )
                continue

            file_id = file_info_dict["id"]
            s3_key = file_info_dict.get("s3_key")

            if not s3_key:
                print(
                    f"Warning: Skipping file ID {file_id} in collection {collection_id} due to missing or empty s3_key."
                )
                continue

            try:
                url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": STORAGE_BUCKET_NAME, "Key": s3_key},
                    ExpiresIn=3600,  # 1 hour
                )
                presigned_urls[file_id] = url
            except ClientError as e:
                print(
                    f"Error generating presigned URL for file {file_id} (key: {s3_key}): {e}"
                )
                continue  # Skip this file

        return CollectionFilePresignedUrlsResponse(presigned_urls=presigned_urls)

    except ClientError as e:
        print(
            f"DynamoDB error retrieving collection {collection_id} for presigned URLs: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve collection data: {e.response['Error']['Message']}",
        ) from e
    except HTTPException as e:  # Re-raise our 404
        raise e
    except Exception as e:
        print(
            f"Unexpected error generating presigned URLs for collection {collection_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
