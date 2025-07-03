from typing import List
from fastapi import APIRouter, HTTPException, status
from constants import AWS_REGION, STORAGE_BUCKET_NAME
from .methods.item_description_filter_label_test import item_label_filter_rule_test
from schemas.datamodel import Item
from schemas.requests_responses import (
    GenerateUploadUrlsRequest,
    GenerateUploadUrlsResponse,
    ItemListResponse,
    CreateItemRequest,
    UpdateItemRequest,
    TestDescriptionFilterPromptRequest,
    TestDescriptionFilterPromptResponse,
    TestLabelFilteringRuleRequest,
    TestLabelFilteringRuleResponse,
)

# Import the implementation functions from the method files
from .methods.get_items import get_items as get_items_impl
from .methods.create_item import create_item as create_item_impl
from .methods.get_item import get_item as get_item_impl
from .methods.update_item import update_item as update_item_impl
from .methods.delete_item import delete_item as delete_item_impl
from .methods.generate_upload_urls import ClientError, generate_upload_urls_impl
from .methods.item_description_filter_prompt_test import (
    item_description_filter_prompt_test as item_description_filter_prompt_test_impl,
)
import boto3
from botocore.client import Config

# Main router for Item operations
router = APIRouter()


# Define routes directly, calling the imported implementation functions
@router.get("/", response_model=ItemListResponse)
async def get_items() -> ItemListResponse:
    """
    Retrieves a list of all Items.

    Returns:
        ItemListResponse: A response object containing a list of Items.
    """
    return await get_items_impl()


@router.post("/", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(item_request: CreateItemRequest) -> Item:
    """
    Creates a new Item based on the provided request data.

    Args:
        item_request (CreateItemRequest): The request body containing the details for the new Item.

    Returns:
        Item: The newly created Item object.
    """
    return await create_item_impl(item_request)


@router.post("/uploadurls", response_model=GenerateUploadUrlsResponse)
async def generate_upload_urls(
    request: GenerateUploadUrlsRequest,
) -> GenerateUploadUrlsResponse:
    """
    Generates pre-signed S3 URLs for uploading files associated with Items.

    Args:
        request (GenerateUploadUrlsRequest): The request body containing filenames and content types.

    Returns:
        GenerateUploadUrlsResponse: A response object containing the generated pre-signed URLs.
    """
    return await generate_upload_urls_impl(request)


@router.post("/downloadurls", response_model=List[str])
async def generate_download_url(s3_keys: List[str]) -> List[str]:
    """
    Generates pre-signed S3 URLs for downloading files based on their S3 keys.

    Ensures keys are prefixed with 'temp-uploads/' for security.

    Args:
        s3_keys (List[str]): A list of S3 keys for the files to download.

    Raises:
        HTTPException: If there's an error generating a URL (e.g., S3 client error).

    Returns:
        List[str]: A list of pre-signed URLs corresponding to the provided S3 keys.
    """
    s3_client = boto3.client(
        "s3",
        region_name=AWS_REGION,
        config=Config(signature_version="s3v4"),
    )
    expiration = 3600  # Link expiration time in seconds (e.g., 1 hour)
    urls = []
    for s3_key in s3_keys:
        # Prevent leaking of other objects in the same bucket
        if not s3_key.startswith("temp-uploads/"):
            s3_key = "temp-uploads/" + s3_key
        try:
            url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": STORAGE_BUCKET_NAME, "Key": s3_key},
                ExpiresIn=expiration,
                HttpMethod="GET",
            )
            urls.append(url)
        except ClientError as e:
            # Handle error (e.g., log it, raise an exception, etc.)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            ) from e

    return urls


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: str) -> Item:
    """
    Retrieves a specific Item by its ID.

    Args:
        item_id (str): The unique identifier of the Item to retrieve.

    Returns:
        Item: The Item object corresponding to the given ID.
    """
    return await get_item_impl(item_id)


@router.post("/test/prompt")
async def item_description_filter_prompt_test(
    request: TestDescriptionFilterPromptRequest,
) -> TestDescriptionFilterPromptResponse:
    """
    Tests the Item description filtering prompt with the provided text and configuration.

    Args:
        request (TestDescriptionFilterPromptRequest): The request containing the text,
                                                         prompt configuration, and LLM settings.

    Returns:
        TestDescriptionFilterPromptResponse: The response indicating whether the description
                                                passes the filter based on the prompt test.
    """
    return await item_description_filter_prompt_test_impl(request)


@router.post("/test/label")
async def item_label_filtering_rule_test(
    request: TestLabelFilteringRuleRequest,
) -> TestLabelFilteringRuleResponse:
    """
    Tests the Item label filtering rule with the provided text and configuration.

    Args:
        request (TestLabelFilteringRuleRequest): The request containing the text,
                                                         prompt configuration, and LLM settings.

    Returns:
        TestLabelFilteringRuleResponse: The response indicating whether the description
                                                passes the filter based on the label test.
    """
    return await item_label_filter_rule_test(request)


@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: str, item_request: UpdateItemRequest) -> Item:
    """
    Updates an existing Item identified by its ID with the provided data.

    Args:
        item_id (str): The unique identifier of the Item to update.
        item_request (UpdateItemRequest): The request body containing the updated Item details.

    Returns:
        Item: The updated Item object.
    """
    return await update_item_impl(item_id, item_request)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str) -> None:
    """
    Deletes an Item identified by its ID.

    Args:
        item_id (str): The unique identifier of the Item to delete.

    Returns:
        None: Returns None with a 204 No Content status code upon successful deletion.
    """
    await delete_item_impl(item_id)
    return None  # Explicitly return None for 204
