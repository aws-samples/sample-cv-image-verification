from fastapi import HTTPException, status

# Import necessary models and utils from the verification_job_utils
from .verification_job_utils import s3_client, verification_jobs_table

# Import the utility function directly from its location
from utils.s3_helpers import generate_presigned_urls_for_job_files
from constants import STORAGE_BUCKET_NAME  # Import constant directly
from schemas.requests_responses import VerificationJobFilePresignedUrlsResponse


async def get_verification_job_files_url(
    verification_job_id: str,
) -> VerificationJobFilePresignedUrlsResponse:
    """
    Implementation to generate and return presigned GET URLs for all files associated with a verification job.
    """
    try:
        # Call the synchronous utility function
        presigned_urls = generate_presigned_urls_for_job_files(
            verification_job_id=verification_job_id,
            s3_client=s3_client,
            verification_jobs_table=verification_jobs_table,
            storage_bucket_name=STORAGE_BUCKET_NAME,
            expires_in=43200,  # 12 hours expiry
        )

        # The utility function handles the case where the job is not found by returning {}
        # If the job wasn't found (utility logged a warning and returned {}),
        # we might want to return 404 here explicitly.
        # Let's check if the job exists first for a clearer 404.
        job_exists_check = verification_jobs_table.get_item(
            Key={"id": verification_job_id}
        )
        if "Item" not in job_exists_check:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification job with ID {verification_job_id} not found",
            )
        # If job exists but presigned_urls is empty, it means the job has no files.

        return VerificationJobFilePresignedUrlsResponse(presigned_urls=presigned_urls)

    except HTTPException as e:  # Re-raise our explicit 404
        raise e
    except Exception as e:
        # Catch any unexpected errors from the utility function or this handler
        print(
            f"Unexpected error in get_verification_job_files_url handler for job {verification_job_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while generating file URLs: {str(e)}",
        ) from e
