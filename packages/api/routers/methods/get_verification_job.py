from fastapi import HTTPException, status

# Import necessary models and utils from the verification_job_utils
from .verification_job_utils import fetch_verification_job
from schemas.datamodel import VerificationJobDto
from schemas.requests_responses import VerificationJobResponse


async def get_verification_job(verification_job_id: str) -> VerificationJobResponse:
    """
    Implementation to retrieve a specific verification job by its ID, including the collection name.
    """
    try:
        # Use the utility function to fetch the verification job with all associated data
        verification_job, collection_name = fetch_verification_job(
            verification_job_id
        )

        # Create the DTO with all the retrieved data
        dto = VerificationJobDto(
            **verification_job.model_dump(),
            collection_name=collection_name,
            total_cost=verification_job.cost,
        )

        # Return the response containing the DTO
        return VerificationJobResponse(verification_job=dto)

    except ValueError as e:
        # Handle case where job is not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification job with ID {verification_job_id} not found",
        ) from e
    except Exception as e:
        print(
            f"Unexpected error retrieving verification job {verification_job_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
