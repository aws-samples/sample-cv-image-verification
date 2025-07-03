import json
from fastapi import HTTPException, status
from typing import Optional, Any
from decimal import Decimal
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

# Import necessary models and utils from the verification_job_utils
from .verification_job_utils import (
    verification_job_logs_table,
    dynamodb_item_to_verification_job_log_entry,
)
from schemas.requests_responses import VerificationJobLogListResponse


# Helper to convert Decimals in a structure to int/float for JSON serialization
def _convert_decimals_for_json(data: Any) -> Any:
    if isinstance(data, list):
        return [_convert_decimals_for_json(v) for v in data]
    elif isinstance(data, dict):
        return {k: _convert_decimals_for_json(v) for k, v in data.items()}
    elif isinstance(data, Decimal):
        if data % 1 == 0:
            return int(data)
        else:
            return float(data)
    return data


async def get_verification_job_logs(
    verification_job_id: str,
    limit: int = 100,
    last_evaluated_key: Optional[str] = None,
    search_string: Optional[str] = None,
    log_level: Optional[str] = None,  # Add log_level parameter
) -> VerificationJobLogListResponse:
    """
    Implementation to retrieve log entries for a specific verification job, with pagination and optional message content search.
    Uses the `verification-job-id-index` GSI.
    """
    try:
        query_kwargs = {
            "IndexName": "verification-job-id-index",
            "KeyConditionExpression": Key("verification_job_id").eq(
                verification_job_id
            ),
            "Limit": limit,
            "ScanIndexForward": False,  # Get newest logs first
        }

        # Build filter expression dynamically
        filter_expression: Optional[Attr] = None
        if search_string:
            filter_expression = Attr("message").contains(search_string)

        if log_level:
            level_filter = Attr("level").eq(log_level.upper())
            if filter_expression:
                filter_expression = filter_expression & level_filter
            else:
                filter_expression = level_filter

        if filter_expression:
            query_kwargs["FilterExpression"] = filter_expression

        if last_evaluated_key:
            try:
                exclusive_start_key = json.loads(last_evaluated_key)
                if not isinstance(exclusive_start_key, dict):
                    raise ValueError("last_evaluated_key must be a JSON object")
                if "timestamp" in exclusive_start_key:
                    try:
                        # Ensure timestamp is int for DynamoDB key structure
                        exclusive_start_key["timestamp"] = int(
                            exclusive_start_key["timestamp"]
                        )
                    except (ValueError, TypeError) as e:
                        raise ValueError(
                            "Timestamp in last_evaluated_key must be a number"
                        ) from e
                query_kwargs["ExclusiveStartKey"] = exclusive_start_key
            except (json.JSONDecodeError, ValueError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid format for last_evaluated_key: {e}",
                ) from e

        response = verification_job_logs_table.query(**query_kwargs)

        items = [
            dynamodb_item_to_verification_job_log_entry(item)
            for item in response.get("Items", [])
        ]
        next_key = response.get("LastEvaluatedKey")

        # Convert Decimals in next_key for Pydantic validation
        serializable_next_key = (
            _convert_decimals_for_json(next_key) if next_key else None
        )
        # Pass the dictionary directly to the response model, not a JSON string
        return VerificationJobLogListResponse(
            items=items, last_evaluated_key=serializable_next_key
        )

    except ClientError as e:
        print(f"Error retrieving logs for verification job {verification_job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve verification job logs: {e.response['Error']['Message']}",
        ) from e
    except HTTPException as e:  # Re-raise our 400
        raise e
    except Exception as e:
        print(
            f"Unexpected error retrieving logs for verification job {verification_job_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
