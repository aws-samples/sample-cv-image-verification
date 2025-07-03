from fastapi import APIRouter, Path, Query, Body, status
from typing import List, Optional
from schemas.datamodel import AssessmentStatus, VerificationJobDto  # Import DTO
from schemas.requests_responses import (
    VerificationJobResponse,
    CreateVerificationJobRequest,
    CreateVerificationJobResponse,
    UpdateVerificationJobRequest,
    UpdateVerificationJobResponse,
    VerificationJobLogListResponse,
    VerificationJobFilePresignedUrlsResponse,
)

# Import implementation functions from the methods directory
from .methods.list_verification_jobs import (
    list_verification_jobs as list_verification_jobs_impl,
)
from .methods.get_verification_job import (
    get_verification_job as get_verification_job_impl,
)
from .methods.create_verification_job import (
    create_verification_job as create_verification_job_impl,
)
from .methods.start_verification_job_execution import (
    start_verification_job_execution as start_verification_job_execution_impl,
)
from .methods.update_verification_job import (
    update_verification_job as update_verification_job_impl,
)
from .methods.get_verification_job_files_url import (
    get_verification_job_files_url as get_verification_job_files_url_impl,
)
from .methods.get_verification_job_logs import (
    get_verification_job_logs as get_verification_job_logs_impl,
)
from .methods.delete_verification_job import (
    delete_verification_job as delete_verification_job_impl,
)

# --- Router Definition ---
router = APIRouter()

# --- Route Handlers (calling implementations) ---


@router.get("/", response_model=List[VerificationJobDto])
async def list_verification_jobs(
    filter_status: Optional[AssessmentStatus] = Query(  # noqa: B008
        None, alias="status", description="Filter verification jobs by status"
    ),
    collection_id: Optional[str] = Query(  # noqa: B008
        None, description="Filter verification jobs by collection ID"
    ),
) -> List[VerificationJobDto]:
    """
    Retrieves a list of verification jobs, optionally filtered by status or collection ID.

    Includes the associated collection name in the response DTOs.

    Args:
        filter_status (Optional[AssessmentStatus]): Filter jobs by their assessment status.
        collection_id (Optional[str]): Filter jobs associated with a specific collection ID.

    Returns:
        List[VerificationJobDto]: A list of verification job data transfer objects matching the criteria.
    """
    return await list_verification_jobs_impl(
        filter_status=filter_status, collection_id=collection_id
    )


@router.get("/{verification_job_id}", response_model=VerificationJobResponse)
async def get_verification_job(
    verification_job_id: str = Path(
        ..., description="The ID of the verification job to retrieve"
    ),
) -> VerificationJobResponse:
    """
    Retrieves details for a specific verification job identified by its ID.

    Includes the associated collection name in the response.

    Args:
        verification_job_id (str): The unique identifier of the verification job to retrieve.

    Returns:
        VerificationJobResponse: The details of the requested verification job.
    """
    return await get_verification_job_impl(verification_job_id=verification_job_id)


@router.post(
    "/",
    response_model=CreateVerificationJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_verification_job(
    job_request: CreateVerificationJobRequest = Body(  # noqa: B008
        ..., description="The verification job to create"
    ),
) -> CreateVerificationJobResponse:
    """
    Creates a new verification job based on the provided request data.

    This process involves deriving item instances from the specified collection
    and initiating the background processing workflow for the job.

    Args:
        job_request (CreateVerificationJobRequest): The request body containing the details
                                                    for the new verification job.

    Returns:
        CreateVerificationJobResponse: The response containing the details of the
                                       newly created verification job.
    """
    return await create_verification_job_impl(job_request=job_request)


@router.post(
    "/{verification_job_id}/start",
    response_model=VerificationJobResponse,
    status_code=status.HTTP_200_OK,
)
async def start_verification_job_execution(
    verification_job_id: str = Path(
        ..., description="The ID of the verification job to start execution for"
    ),
) -> VerificationJobResponse:
    """
    Initiates or restarts the execution of a specific verification job.

    This endpoint requeues the job for processing. It typically involves clearing
    any previous file check results before starting the execution anew.

    Args:
        verification_job_id (str): The unique identifier of the verification job to start.

    Returns:
        VerificationJobResponse: The updated details of the verification job after
                                 being queued for execution.
    """
    return await start_verification_job_execution_impl(
        verification_job_id=verification_job_id
    )


@router.put("/{verification_job_id}", response_model=UpdateVerificationJobResponse)
async def update_verification_job(
    verification_job_id: str = Path(
        ..., description="The ID of the verification job to update"
    ),
    job_request: UpdateVerificationJobRequest = Body(  # noqa: B008
        ..., description="The updated verification job data"
    ),
) -> UpdateVerificationJobResponse:
    """
    Updates an existing verification job identified by its ID with the provided data.

    Allows modification of certain attributes of the verification job.

    Args:
        verification_job_id (str): The unique identifier of the verification job to update.
        job_request (UpdateVerificationJobRequest): The request body containing the updated
                                                    verification job data.

    Returns:
        UpdateVerificationJobResponse: The response containing the updated details of the
                                       verification job.
    """
    return await update_verification_job_impl(
        verification_job_id=verification_job_id, job_request=job_request
    )


@router.get(
    "/{verification_job_id}/files/presigned-urls",
    response_model=VerificationJobFilePresignedUrlsResponse,
)
async def get_verification_job_files_url(
    verification_job_id: str = Path(..., description="The ID of the verification job"),
) -> VerificationJobFilePresignedUrlsResponse:
    """
    Generates and returns pre-signed GET URLs for accessing files associated with a specific verification job.

    These URLs provide temporary, secure access to download the files directly from storage (e.g., S3).

    Args:
        verification_job_id (str): The unique identifier of the verification job whose files are needed.

    Returns:
        VerificationJobFilePresignedUrlsResponse: A response object containing a list of
                                                  pre-signed URLs for the job's files.
    """
    return await get_verification_job_files_url_impl(
        verification_job_id=verification_job_id
    )


@router.get(
    "/logs/{verification_job_id}", response_model=VerificationJobLogListResponse
)
async def get_verification_job_logs(
    verification_job_id: str = Path(
        ..., description="The ID of the verification job to retrieve logs for"
    ),
    limit: int = Query(
        100, description="Maximum number of log entries to return", ge=1, le=1000
    ),
    last_evaluated_key: Optional[str] = Query(
        None, description="JSON string representing the LastEvaluatedKey for pagination"
    ),
    search_string: Optional[str] = Query(
        None, description="Filter log messages containing this string (case-sensitive)"
    ),
    log_level: Optional[str] = Query(  # noqa: B008
        None, description="Filter log entries by log level (e.g., INFO, WARNING, ERROR)"
    ),
) -> VerificationJobLogListResponse:
    """
    Retrieves log entries for a specific verification job, supporting pagination and filtering.

    Allows fetching logs based on job ID, with options to limit the number of results,
    paginate using a `last_evaluated_key`, filter by a search string within log messages,
    and filter by log level. This typically queries a secondary index for efficiency.

    Args:
        verification_job_id (str): The ID of the verification job to retrieve logs for.
        limit (int): Maximum number of log entries to return per request.
        last_evaluated_key (Optional[str]): A token for pagination, representing the last item
                                             from the previous request.
        search_string (Optional[str]): A string to filter log messages (case-sensitive).
        log_level (Optional[str]): Filter logs by their severity level (e.g., INFO, ERROR).

    Returns:
        VerificationJobLogListResponse: A response object containing the list of log entries
                                        and potentially a `last_evaluated_key` for pagination.
    """
    return await get_verification_job_logs_impl(
        verification_job_id=verification_job_id,
        limit=limit,
        last_evaluated_key=last_evaluated_key,
        search_string=search_string,
        log_level=log_level,
    )


@router.delete("/{verification_job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_verification_job(
    verification_job_id: str = Path(
        ..., description="The ID of the verification job to delete"
    ),
) -> None:
    """
    Deletes a specific verification job identified by its ID.

    This operation permanently removes the verification job and potentially associated data.

    Args:
        verification_job_id (str): The unique identifier of the verification job to delete.

    Returns:
        None: Returns None with a 204 No Content status code upon successful deletion.
    """
    await delete_verification_job_impl(verification_job_id=verification_job_id)
    return None  # Explicitly return None for 204
