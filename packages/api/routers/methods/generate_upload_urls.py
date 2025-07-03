from typing import List
import boto3
from botocore.exceptions import ClientError
import logging

from schemas.requests_responses import (
    GenerateUploadUrlsRequest,
    GenerateUploadUrlsResponse,
    PresignedFileUrl,
)
from constants import STORAGE_BUCKET_NAME, AWS_REGION

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize S3 client
s3_client = boto3.client(
    "s3", region_name=AWS_REGION, config=boto3.session.Config(signature_version="s3v4")
)


async def generate_upload_urls_impl(
    request: GenerateUploadUrlsRequest,
) -> GenerateUploadUrlsResponse:
    """
    Implementation to generate presigned URLs for uploading files to S3.
    """
    presigned_urls: List[PresignedFileUrl] = []
    expiration = 3600  # Link expiration time in seconds (e.g., 1 hour)

    for filename in request.filenames:
        object_key = f"temp-uploads/{filename}"  # Define a path prefix if needed, e.g., 'uploads/'
        try:
            url = s3_client.generate_presigned_url(
                "put_object",
                Params={"Bucket": STORAGE_BUCKET_NAME, "Key": object_key},
                ExpiresIn=expiration,
                HttpMethod="PUT",
            )
            presigned_urls.append(
                PresignedFileUrl(
                    filename=filename, s3_key=object_key, presigned_url=url
                )
            )
        except ClientError as e:
            logger.error(f"Error generating presigned URL for {filename}: {e}")

    return GenerateUploadUrlsResponse(urls=presigned_urls)
