import time
from decimal import Decimal
from fastapi import HTTPException, status
from typing import Optional
from botocore.exceptions import ClientError

# Import necessary models and utils from the verification_job_utils
from .verification_job_utils import (
    verification_jobs_table,
    dynamodb_item_to_verification_job,
    model_to_dynamodb_item,
    queue_verification_job,  # Import the helper,
    collections_table
)
from schemas.datamodel import VerificationJobDto
from schemas.requests_responses import VerificationJobResponse


async def start_verification_job_execution(
    verification_job_id: str,
) -> VerificationJobResponse:
    """
    Implementation requeue the verification job.
    Clears previous file check results before starting.
    """
    try:
        # 1. Fetch the Verification Job
        vj_response = verification_jobs_table.get_item(Key={"id": verification_job_id})
        vj_item = vj_response.get("Item")
        if not vj_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification job with ID {verification_job_id} not found",
            )
        verification_job = dynamodb_item_to_verification_job(vj_item)

        queue_verification_job(verification_job_id)

        # 5. Update the job object
        current_time = int(time.time())
        verification_job.updated_at = current_time

        # 6. Save the updated job back to DynamoDB
        updated_item_data = model_to_dynamodb_item(verification_job)
        verification_jobs_table.put_item(Item=updated_item_data)

        # 7. Fetch collection name and calculate cost for the DTO response
        collection_name: Optional[str] = None
        try:
            col_response = collections_table.get_item(
                Key={"id": verification_job.collection_id}
            )
            col_item = col_response.get("Item")
            if col_item:
                desc_value = col_item.get('description')
                collection_name = str(desc_value) if desc_value is not None else None
        except ClientError as wo_e:
            print(
                f"Warning: Error fetching collection {verification_job.collection_id} for job {verification_job_id} DTO: {wo_e}"
            )

        # Calculate total cost (will be 0 or None after clearing checks)
        total_cost_val: Optional[float] = None
        if verification_job.files:
            current_total = Decimal("0.0")
            cost_found = False
            for file_instance in verification_job.files:
                if file_instance.file_checks:  # This list is now empty
                    for file_check in file_instance.file_checks:
                        if file_check.cost is not None:
                            current_total += Decimal(str(file_check.cost))
                            cost_found = True
            if cost_found:
                total_cost_val = float(current_total)

        dto = VerificationJobDto(
            **verification_job.model_dump(),
            collection_name=collection_name,
            total_cost=total_cost_val,
        )
        return VerificationJobResponse(verification_job=dto)

    except HTTPException as e:  # Re-raise 404, 409 or SFN start error
        raise e
    except ClientError as e:  # Catch DynamoDB or SFN describe_execution errors
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        print(
            f"AWS ClientError ({error_code}) starting execution for job {verification_job_id}: {e}"
        )
        if error_code == "ResourceNotFoundException":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification job with ID {verification_job_id} not found.",
            ) from e
        else:
            error_message = e.response.get("Error", {}).get("Message", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error during job start: {error_message}",
            ) from e
    except Exception as e:
        print(f"Unexpected error starting execution for job {verification_job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during job start: {str(e)}",
        ) from e
