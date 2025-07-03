from fastapi import APIRouter, Path, Query, Body, status
from typing import Optional

# Import necessary models from schemas
from schemas.datamodel import AssessmentStatus
from schemas.requests_responses import (
    CollectionsListResponse,
    CollectionResponse,
    CreateCollectionRequest,
    CreateCollectionResponse,
    UpdateCollectionRequest,
    UpdateCollectionResponse,
    PresignUploadResponse,
    AddFileRequest,
    AddFileResponse,
    CollectionFilePresignedUrlsResponse,
    AddressAutocompleteResponse,
)

# Import implementation functions from the methods directory
from .methods.list_collections import list_collections as list_collections_impl
from .methods.address_autocomplete import (
    address_autocomplete as address_autocomplete_impl,
)

# Import get_coordinates implementation and its local models
from .methods.get_coordinates import (
    get_coordinates as get_coordinates_impl,
    CoordinatesRequest,
    CoordinatesResponse,
)
from .methods.get_collection_file_presigned_urls import (
    get_collection_file_presigned_urls as get_collection_file_presigned_urls_impl,
)
from .methods.get_collection import get_collection as get_collection_impl
from .methods.create_collection import create_collection as create_collection_impl
from .methods.update_collection import update_collection as update_collection_impl
from .methods.delete_collection import delete_collection as delete_collection_impl
from .methods.presign_collection_file_upload import (
    presign_collection_file_upload as presign_collection_file_upload_impl,
)
from .methods.add_file_to_collection import (
    add_file_to_collection as add_file_to_collection_impl,
)

# --- Router Definition ---
router = APIRouter()

# --- Route Handlers (calling implementations) ---


@router.get("/", response_model=CollectionsListResponse)
async def list_collections(
    filter_status: Optional[AssessmentStatus] = Query(  # noqa: B008
        None, alias="status", description="Filter collections by status"
    ),
) -> CollectionsListResponse:
    """
    Retrieves a list of collections, optionally filtered by their assessment status.

    Args:
        filter_status (Optional[AssessmentStatus]): Filter collections by status (e.g., PENDING, COMPLETED).

    Returns:
        CollectionsListResponse: A response object containing a list of collections matching the criteria.
    """
    return await list_collections_impl(filter_status=filter_status)


@router.get("/address-autocomplete", response_model=AddressAutocompleteResponse)
async def address_autocomplete(
    query: str = Query(
        ..., min_length=1, description="Partial address text to search for"
    ),
) -> AddressAutocompleteResponse:
    """
    Provides address autocomplete suggestions based on a partial address query string.

    Args:
        query (str): The partial address text entered by the user for autocompletion.

    Returns:
        AddressAutocompleteResponse: A response object containing a list of suggested addresses.
    """
    return await address_autocomplete_impl(query=query)


# Use the imported CoordinatesRequest/Response models here
@router.post(
    "/coordinates", response_model=CoordinatesResponse
)  # Changed to POST to accept body
async def get_coordinates(
    request: CoordinatesRequest,  # Accept request body
) -> CoordinatesResponse:
    """
    Retrieves the geographical coordinates (latitude and longitude) for a given address.

    Accepts the address details within the request body.

    Args:
        request (CoordinatesRequest): The request body containing the address information.

    Returns:
        CoordinatesResponse: A response object containing the latitude and longitude.
    """
    # Pass the request object directly
    return await get_coordinates_impl(request=request)


@router.get(
    "/{collection_id}/files/presigned-urls",
    response_model=CollectionFilePresignedUrlsResponse,
)
async def get_collection_file_presigned_urls(
    collection_id: str = Path(
        ..., description="The ID of the collection to retrieve file URLs for"
    ),
) -> CollectionFilePresignedUrlsResponse:
    """
    Generates and retrieves pre-signed GET URLs for all files associated with a specific collection.

    These URLs allow temporary, secure access to download the files directly from storage.

    Args:
        collection_id (str): The unique identifier of the collection whose file URLs are needed.

    Returns:
        CollectionFilePresignedUrlsResponse: A response object containing a list of pre-signed URLs.
    """
    return await get_collection_file_presigned_urls_impl(collection_id=collection_id)


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: str = Path(..., description="The ID of the collection to retrieve"),
) -> CollectionResponse:
    """
    Retrieves the details of a specific collection identified by its ID.

    Args:
        collection_id (str): The unique identifier of the collection to retrieve.

    Returns:
        CollectionResponse: A response object containing the details of the requested collection.
    """
    return await get_collection_impl(collection_id=collection_id)


@router.post(
    "/", response_model=CreateCollectionResponse, status_code=status.HTTP_201_CREATED
)
async def create_collection(
    collection_request: CreateCollectionRequest = Body(  # noqa: B008
        ..., description="The collection to create"
    ),
) -> CreateCollectionResponse:
    """
    Creates a new collection based on the provided request data.

    This includes associating Item instances based on the provided `item_ids`.

    Args:
        collection_request (CreateCollectionRequest): The request body containing the details
                                                     for the new collection.

    Returns:
        CreateCollectionResponse: A response object containing the details of the newly created collection.
    """
    return await create_collection_impl(collection_request=collection_request)


@router.put("/{collection_id}", response_model=UpdateCollectionResponse)
async def update_collection(
    collection_id: str = Path(..., description="The ID of the collection to update"),
    collection_request: UpdateCollectionRequest = Body(  # noqa: B008
        ..., description="The updated collection data"
    ),
) -> UpdateCollectionResponse:
    """
    Updates an existing collection identified by its ID with the provided data.

    Note: This endpoint typically updates top-level collection fields. Updating associated
          Item instances or files might require separate operations or specific handling within the implementation.

    Args:
        collection_id (str): The unique identifier of the collection to update.
        collection_request (UpdateCollectionRequest): The request body containing the updated
                                                     collection data.

    Returns:
        UpdateCollectionResponse: A response object containing the updated details of the collection.
    """
    return await update_collection_impl(
        collection_id=collection_id, collection_request=collection_request
    )


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: str = Path(..., description="The ID of the collection to delete"),
) -> None:
    """
    Deletes a specific collection identified by its ID.

    This process typically involves checks for associated verification jobs and cleanup
    of related resources, such as files stored in S3.

    Args:
        collection_id (str): The unique identifier of the collection to delete.

    Returns:
        None: Returns None with a 204 No Content status code upon successful deletion.
    """
    await delete_collection_impl(collection_id=collection_id)
    return None  # Explicitly return None for 204


@router.post("/{collection_id}/presign-upload", response_model=PresignUploadResponse)
async def presign_collection_file_upload(
    collection_id: str = Path(
        ..., description="The ID of the collection to upload a file for"
    ),
    content_type: str = Query(..., description="The MIME type of the file"),
    filename: str = Query(..., description="The name of the file"),
) -> PresignUploadResponse:
    """
    Generates a pre-signed URL that allows a client to directly upload a file to S3
    in the context of a specific collection.

    Args:
        collection_id (str): The ID of the collection the file will be associated with.
        content_type (str): The MIME type of the file to be uploaded (e.g., 'image/jpeg').
        filename (str): The intended name of the file once uploaded.

    Returns:
        PresignUploadResponse: A response object containing the pre-signed URL and the
                               corresponding S3 key where the file should be uploaded.
    """
    return await presign_collection_file_upload_impl(
        collection_id=collection_id, content_type=content_type, filename=filename
    )


@router.post("/{collection_id}/files", response_model=AddFileResponse)
async def add_file_to_collection(
    collection_id: str = Path(
        ..., description="The ID of the collection to add a file to"
    ),
    file_data: AddFileRequest = Body(  # noqa: B008
        ..., description="The file data to add to the collection"
    ),
) -> AddFileResponse:
    """
    Registers a file with a collection after the file has been successfully uploaded
    (typically using a pre-signed URL obtained from another endpoint).

    This updates the collection record to include metadata about the uploaded file.

    Args:
        collection_id (str): The ID of the collection to associate the file with.
        file_data (AddFileRequest): The request body containing details about the uploaded file
                                    (e.g., S3 key, filename, content type).

    Returns:
        AddFileResponse: A response object confirming the file association, potentially
                         including the updated file list or file details.
    """
    return await add_file_to_collection_impl(
        collection_id=collection_id, file_data=file_data
    )
