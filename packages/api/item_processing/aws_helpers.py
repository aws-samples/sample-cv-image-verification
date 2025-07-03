import PIL
import PIL.Image
import boto3
import asyncio
from typing import Optional, Any, cast
from botocore.exceptions import ClientError
import io

# Initialize AWS clients
s3_client = boto3.client("s3")
rekognition_client = boto3.client("rekognition")


async def get_image_bytes_from_s3(bucket: str, key: str) -> Optional[bytes]:
    """Retrieve image bytes from S3, and makes sure it is in PNG format."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        image_bytes: bytes = response["Body"].read()
        
        # Convert image to PNG format
        image = PIL.Image.open(io.BytesIO(image_bytes))
        image_bytes_png_buffer = io.BytesIO()
        image.save(image_bytes_png_buffer, format="PNG")
        image_bytes_png = image_bytes_png_buffer.getvalue()
        
        return image_bytes_png
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


async def detect_labels_s3(image_bytes: bytes,resize_image:bool) -> list[dict[str, Any]]:
    """
    Detect labels in an image using AWS Rekognition.
    This asynchronous function sends the provided image bytes to AWS Rekognition
    for label detection, with automatic retries for throughput exceeded errors.
    Parameters:
    ----------
    image_bytes : bytes
        The binary data of the image to analyze.
    resize_image : bool
        Whether the image should be resized before processing. This prevents images being sent to Rekognition that are too large.
    Returns:
    -------
    list[dict[str, Any]]
        A list of dictionaries containing detected labels. Each dictionary contains
        information about a detected label, including name and confidence score.
        Returns an empty list if image_bytes is empty.
    Raises:
    ------
    ClientError
        If AWS Rekognition service returns an error other than throughput exceeded,
        or if all retry attempts are exhausted.
    Notes:
    -----
    - The function will attempt up to 50 retries with a 5-second delay between attempts
      when encountering ProvisionedThroughputExceededException.
    - The detection is configured to return a maximum of 20 labels with a minimum 
      confidence score of 50%.
    """
    """Detect labels using Rekognition from image bytes."""
    if not image_bytes:
        return []

    max_retries = 50
    retry_delay = 5  # seconds
    
    if resize_image:
        # Resize the image to a maximum of 1024x1024 pixels if it is larger
        image = PIL.Image.open(io.BytesIO(image_bytes))
        max_size = (1024, 1024)
        image.thumbnail(max_size, PIL.Image.LANCZOS)
        image_bytes_buffer = io.BytesIO()
        image.save(image_bytes_buffer, format="PNG")
        image_bytes = image_bytes_buffer.getvalue()
    
    for attempt in range(max_retries):
        try:
            response = rekognition_client.detect_labels(
                Image={"Bytes": image_bytes},
                MaxLabels=20,
                MinConfidence=50,
            )
            labels = cast(list[dict[str, Any]], response.get("Labels", []))
            return labels
        except ClientError as e:
            if e.response["Error"]["Code"] == "ProvisionedThroughputExceededException":
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    raise  # Re-raise the exception after all retries exhausted
            else:
                raise  # Re-raise if it's a different error
