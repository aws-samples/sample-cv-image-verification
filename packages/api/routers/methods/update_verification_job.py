import time
from decimal import Decimal
from fastapi import HTTPException, status
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

# Import necessary models and utils from the verification_job_utils
from .verification_job_utils import (
    verification_jobs_table,
    dynamodb_item_to_verification_job,
)
from schemas.datamodel import AssessmentStatus
from schemas.requests_responses import (
    UpdateVerificationJobRequest,
    UpdateVerificationJobResponse,
)


async def update_verification_job(
    verification_job_id: str, job_request: UpdateVerificationJobRequest
) -> UpdateVerificationJobResponse:
    """
    Implementation to update an existing verification job.
    """
    try:
        update_expression_parts = []
        expression_attribute_values = {}
        expression_attribute_names = {}

        current_time = int(time.time())
        update_expression_parts.append("#updated_at = :updated_at")
        expression_attribute_names["#updated_at"] = "updated_at"
        expression_attribute_values[":updated_at"] = current_time

        update_data = job_request.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            attr_name_placeholder = f"#{key}"
            attr_value_placeholder = f":{key}"
            expression_attribute_names[attr_name_placeholder] = key
            update_expression_parts.append(
                f"{attr_name_placeholder} = {attr_value_placeholder}"
            )

            # Convert enum/float/etc. for DynamoDB update
            converted_value = value  # Default assignment
            if key == "status" and isinstance(value, AssessmentStatus):
                converted_value = value.value  # Store enum as its string value
            elif key == "confidence" and value is not None and isinstance(value, float):
                # Convert float to Decimal first for precision
                decimal_value = Decimal(str(value))
                # Convert to int if it's a whole number, else keep as Decimal
                converted_value = (
                    int(decimal_value) if decimal_value % 1 == 0 else decimal_value
                )
            elif isinstance(value, float):  # Handle other potential floats
                decimal_value = Decimal(str(value))
                converted_value = (
                    int(decimal_value) if decimal_value % 1 == 0 else decimal_value
                )
            elif isinstance(value, Decimal):  # Handle potential Decimal inputs
                converted_value = int(value) if value % 1 == 0 else value
            elif isinstance(value, str) and value.isdigit():
                # Attempt to convert string digits to int if target might be int (Handles error 1 possibility)
                try:
                    converted_value = int(value)
                except ValueError:
                    converted_value = value  # Keep as string if conversion fails

            expression_attribute_values[attr_value_placeholder] = converted_value

        if (
            not update_expression_parts
            or len(update_expression_parts) == 1
            and "#updated_at" in expression_attribute_names
        ):
            # Only timestamp updated or nothing changed
            response = verification_jobs_table.get_item(Key={"id": verification_job_id})
            item = response.get("Item")
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Verification job with ID {verification_job_id} not found",
                )
            return UpdateVerificationJobResponse(
                verification_job=dynamodb_item_to_verification_job(item)
            )

        update_expression = "SET " + ", ".join(update_expression_parts)

        response = verification_jobs_table.update_item(
            Key={"id": verification_job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW",
            ConditionExpression=Attr("id").exists(),
        )
        return UpdateVerificationJobResponse(
            verification_job=dynamodb_item_to_verification_job(response["Attributes"])
        )

    except ClientError as e:
        print(f"Error updating verification job {verification_job_id}: {e}")
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Verification job with ID {verification_job_id} not found",
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update verification job: {e.response['Error']['Message']}",
            ) from e
    except Exception as e:
        print(f"Unexpected error updating verification job {verification_job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
