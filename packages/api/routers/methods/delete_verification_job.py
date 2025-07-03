from fastapi import HTTPException, status
from botocore.exceptions import ClientError

# Import necessary models and utils from the verification_job_utils
from .verification_job_utils import verification_jobs_table


async def delete_verification_job(verification_job_id: str) -> None:
    """
    Implementation to delete a verification job
    """
    try:
        # 1. Get the job details first to find the execution ARN
        get_response = verification_jobs_table.get_item(Key={"id": verification_job_id})
        item = get_response.get("Item")

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification job with ID {verification_job_id} not found",
            )

        # 3. Delete the item from DynamoDB
        verification_jobs_table.delete_item(Key={"id": verification_job_id})
        # No return needed for 204

    except HTTPException as e:  # Re-raise our 404
        raise e
    except ClientError as e:
        print(
            f"DynamoDB ClientError during delete operation for job {verification_job_id}: {e}"
        )
        # If delete_item fails after get_item succeeded, it's likely a 500-level issue.
        # Safely access error details from boto3 ClientError response
        error_message = "Unknown error"
        if hasattr(e, 'response') and e.response:
            error_dict = e.response.get('Error', {})
            error_message = error_dict.get('Message', str(e))
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete verification job: {error_message}",
        ) from e
    except Exception as e:
        print(f"Unexpected error deleting verification job {verification_job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
