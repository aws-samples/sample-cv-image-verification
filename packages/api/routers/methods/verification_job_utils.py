import boto3
import json
from decimal import Decimal
from typing import Any, cast, Dict
from pydantic import BaseModel
from enum import Enum

from constants import STORAGE_BUCKET_NAME
from botocore.exceptions import ClientError

# Import necessary models and constants from the main project structure
from schemas.datamodel import (
    VerificationJob,
    AssessmentStatus,
    CollectionFileStatus,
    CollectionFileInstance,
    Collection,
    ItemInstance,
    Item,
    CollectionFile,
    VerificationJobLogEntry,
)
from constants import (
    AWS_REGION,
    VERIFICATION_JOBS_TABLE_NAME,
    PROCESSING_QUEUE_URL,
    COLLECTIONS_TABLE_NAME,
    VERIFICATION_JOB_LOGS_TABLE_NAME,
    FILE_CHECKS_TABLE_NAME,
)

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
collections_table = dynamodb.Table(COLLECTIONS_TABLE_NAME)
sqs_client = boto3.client("sqs", region_name=AWS_REGION)
s3_client = boto3.client("s3", region_name=AWS_REGION)
verification_jobs_table = dynamodb.Table(VERIFICATION_JOBS_TABLE_NAME)
verification_job_logs_table = dynamodb.Table(VERIFICATION_JOB_LOGS_TABLE_NAME)
file_checks_table = dynamodb.Table(FILE_CHECKS_TABLE_NAME)

# --- Helper Functions for DynamoDB <-> Pydantic Conversion ---


def parse_decimal(value: Any) -> Any:
    """Recursively convert Decimal objects to float or int."""
    if isinstance(value, list):
        return [parse_decimal(v) for v in value]
    elif isinstance(value, dict):
        return {k: parse_decimal(v) for k, v in value.items()}
    elif isinstance(value, Decimal):
        # Check if it's an integer stored as Decimal
        if value % 1 == 0:
            return int(value)
        else:
            return float(value)
    return value


def dynamodb_item_to_verification_job(item: dict) -> VerificationJob:
    """Converts a DynamoDB item to a VerificationJob Pydantic model."""
    item = parse_decimal(item)  # Convert Decimals first
    if "status" in item and isinstance(item["status"], str):
        try:
            item["status"] = AssessmentStatus(item["status"])
        except ValueError:
            print(
                f"Warning: Invalid status value '{item['status']}' found for job {item.get('id')}"
            )
            item["status"] = AssessmentStatus.PENDING
    # Handle nested ItemInstance status
    if "items" in item and isinstance(item["items"], list):
        for item_instance_data in item["items"]:
            if "status" in item_instance_data and isinstance(
                item_instance_data["status"], str
            ):
                try:
                    item_instance_data["status"] = AssessmentStatus(
                        item_instance_data["status"]
                    )
                except ValueError:
                    print(
                        f"Warning: Invalid status value '{item_instance_data['status']}' found for item instance {item_instance_data.get('id')}"
                    )
                    item_instance_data["status"] = AssessmentStatus.PENDING
    # Ensure nested ItemInstance models are correctly parsed if they exist
    if "items" in item and isinstance(item["items"], list):
        # Ensure rules are lists even if None/missing before validation
        for item_data in item["items"]:
            item_data["label_filtering_rules_applied"] = (
                item_data.get("label_filtering_rules_applied") or []
            )
            item_data["description_filtering_rules_applied"] = (
                item_data.get("description_filtering_rules_applied") or []
            )
        item["items"] = [ItemInstance(**item_data) for item_data in item["items"]]

    # Ensure nested CollectionFileInstance models are correctly parsed
    if "files" in item and isinstance(item["files"], list):
        parsed_files = []
        for file_data in item["files"]:
            # Handle CollectionFileStatus enum conversion within the file instance data
            if "status" in file_data and isinstance(file_data["status"], str):
                try:
                    file_data["status"] = CollectionFileStatus(file_data["status"])
                except ValueError:
                    print(
                        f"Warning: Invalid status value '{file_data['status']}' found for file {file_data.get('id')} in job {item.get('id')}"
                    )
                    file_data["status"] = (
                        None  # Or a default status like CollectionFileStatus.PENDING
                    )
            # Ensure file_checks is a list
            file_data["file_checks"] = file_data.get("file_checks") or []
            # Create the CollectionFileInstance object
            parsed_files.append(CollectionFileInstance(**file_data))
        item["files"] = parsed_files
    else:
        item["files"] = []  # Ensure files is always a list

    # Ensure items is always a list
    if "items" not in item or not isinstance(item["items"], list):
        item["items"] = []

    return VerificationJob(**item)


def dynamodb_item_to_verification_job_log_entry(item: dict) -> VerificationJobLogEntry:
    """Converts a DynamoDB item to a VerificationJobLogEntry Pydantic model."""
    item = parse_decimal(item)  # Convert Decimals first
    # Add any specific enum conversions if needed for log entries in the future
    return VerificationJobLogEntry(**item)


def dynamodb_item_to_collection(item: dict) -> Collection:
    """Converts a DynamoDB item to a Collection Pydantic model."""
    item = parse_decimal(item)  # Convert Decimals first
    # Handle nested CollectionFile status
    if "files" in item and isinstance(item["files"], list):
        for file_data in item["files"]:
            if "status" in file_data and isinstance(file_data["status"], str):
                try:
                    file_data["status"] = CollectionFileStatus(file_data["status"])
                except ValueError:
                    print(
                        f"Warning: Invalid status value '{file_data['status']}' found for file {file_data.get('id')}"
                    )
                    file_data["status"] = None  # Or a default status if applicable
    # Ensure nested Item models are correctly parsed
    if "items" in item and isinstance(item["items"], list):
        # Ensure rules are lists even if None/missing before validation
        for item_data in item["items"]:
            item_data["label_filtering_rules"] = (
                item_data.get("label_filtering_rules") or []
            )
            item_data["description_filtering_rules"] = (
                item_data.get("description_filtering_rules") or []
            )
        item["items"] = [Item(**item_data) for item_data in item["items"]]
    else:
        item["items"] = []  # Ensure items is always a list

    # Ensure nested CollectionFile models are correctly parsed
    if "files" in item and isinstance(item["files"], list):
        item["files"] = [CollectionFile(**file_data) for file_data in item["files"]]
    else:
        item["files"] = []  # Ensure files is always a list

    return Collection(**item)


def model_to_dynamodb_item(model_instance: BaseModel) -> dict[str, Any]:
    """Converts a Pydantic model instance to a DynamoDB compatible dictionary."""
    # Use exclude_none=True to avoid writing null values, which DynamoDB doesn't like unless specified in schema
    item = model_instance.model_dump(mode="json", exclude_none=True)

    # Recursively convert floats to Decimals and enums to strings
    def convert_values(data: Any) -> Any:
        if isinstance(data, dict):
            return {k: convert_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [convert_values(elem) for elem in data]
        elif isinstance(data, float):
            # Use context for precision if needed, otherwise default is usually fine
            return Decimal(str(data))
        elif isinstance(data, Enum):
            return data.value
        else:
            return data

    # Cast the result of the recursive helper
    return cast(Dict[str, Any], convert_values(item))


# --- Helper Function to fetch file checks ---
def fetch_file_checks_for_job(
    verification_job_id: str, verification_job: VerificationJob
):
    """
    Fetches file checks from the file_checks table for all Item instances in a verification job
    and adds them to their corresponding files in the verification job.
    """
    try:
        # Only proceed if there are Items and files in the job
        if verification_job.items and verification_job.files:
            # Get all Item instance IDs
            item_instance_ids = [item.id for item in verification_job.items]

            # For each Item instance, fetch file checks
            for item_instance_id in item_instance_ids:
                try:
                    # Get file checks from file_checks table using verification_job_id and item_instance_id
                    response = file_checks_table.get_item(
                        Key={
                            "verification_job_id": verification_job_id,
                            "item_instance_id": item_instance_id,
                        }
                    )

                    item = response.get("Item")
                    if (
                        item
                        and "file_checks" in item
                        and isinstance(item["file_checks"], list)
                    ):
                        file_checks_list = parse_decimal(item["file_checks"])
                        print(
                            f"Found {len(file_checks_list)} file checks for Item {item_instance_id}"
                        )

                        # Group file checks by file_instance_id
                        file_checks_by_file_id: Any = {}
                        for check in file_checks_list:
                            file_id = check.get("file_instance_id")
                            if file_id:
                                if file_id not in file_checks_by_file_id:
                                    file_checks_by_file_id[file_id] = []
                                file_checks_by_file_id[file_id].append(check)

                        # For each file in the job, add its file checks
                        for file in verification_job.files:
                            if file.id in file_checks_by_file_id:
                                # Convert checks to CollectionFileItemInstance objects
                                for check in file_checks_by_file_id[file.id]:
                                    # Handle CollectionFileStatus enum conversion if needed
                                    if "status" in check and isinstance(
                                        check["status"], str
                                    ):
                                        try:
                                            check["status"] = CollectionFileStatus(
                                                check["status"]
                                            )
                                        except ValueError:
                                            print(
                                                f"Warning: Invalid status value '{check['status']}' in file check"
                                            )
                                            check["status"] = None

                                    from schemas.datamodel import (
                                        CollectionFileItemInstance,
                                    )

                                    # Create CollectionFileItemInstance from the check data
                                    file_check = CollectionFileItemInstance(
                                        item_instance_id=check.get("item_instance_id"),
                                        status=check.get("status"),
                                        status_reasoning=check.get("status_reasoning"),
                                        address_match=check.get("address_match"),
                                        detected_address=check.get("detected_address"),
                                        cost=check.get("cost"),
                                        input_tokens=check.get("input_tokens"),
                                        output_tokens=check.get("output_tokens"),
                                        cluster_number=check.get("cluster_number"),
                                    )
                                    file.file_checks.append(file_check)

                except Exception as e:
                    print(f"Error fetching file checks for Item {item_instance_id}: {e}")

        return verification_job
    except Exception as e:
        print(f"Unexpected error in fetch_file_checks_for_job: {e}")
        return verification_job  # Return the original job without file checks in case of error


# --- Helper Function to fetch a verification job with associated data ---
def fetch_verification_job(verification_job_id: str):
    """
    Retrieves a verification job along with associated data (collection name, file checks, total cost).

    Args:
        verification_job_id: The ID of the verification job to fetch

    Returns:
        Tuple containing:
        - verification_job: The VerificationJob with file_checks populated
        - collection_name: The name/description of the associated collection
        - total_cost: The calculated total cost of all file checks
    """
    try:
        # 1. Fetch the Verification Job
        vj_response = verification_jobs_table.get_item(Key={"id": verification_job_id})
        vj_item = vj_response.get("Item")
        if not vj_item:
            raise ValueError(
                f"Verification job with ID {verification_job_id} not found"
            )

        verification_job = dynamodb_item_to_verification_job(vj_item)
        # 1b. Fetch file checks for this job from file_checks table
        verification_job = fetch_file_checks_for_job(
            verification_job_id, verification_job
        )

        # 2. Fetch the corresponding Collection name
        collection_name = None  # Default to None
        try:
            col_response = collections_table.get_item(
                Key={"id": verification_job.collection_id}
            )
            col_item = col_response.get("Item")
            if col_item:
                collection = dynamodb_item_to_collection(col_item)
                collection_name = (
                    collection.description
                )  # Use description if available
            else:
                print(
                    f"Warning: Associated collection {verification_job.collection_id} not found for verification job {verification_job_id}"
                )
        except Exception as col_e:
            print(
                f"Warning: Error fetching collection {verification_job.collection_id} for verification job {verification_job_id}: {col_e}"
            )
            # Continue with None collection_name

        return verification_job, collection_name

    except ValueError:
        # Re-raise ValueError for specific handling by the API endpoint
        raise
    except Exception as e:
        print(
            f"Unexpected error retrieving verification job {verification_job_id} with associated data: {e}"
        )
        raise Exception(
            f"An unexpected error occurred while retrieving verification job: {str(e)}"
        ) from e


# --- Helper Function to save job without file checks ---
def save_verification_job_without_file_checks(
    verification_job: VerificationJob,
) -> VerificationJob:
    """
    Removes file_checks from all files in the verification job and saves it to DynamoDB.

    This prevents the verification job record from growing too large, as file checks are
    now stored in a separate dedicated table.

    Args:
        verification_job: The VerificationJob to save

    Returns:
        The VerificationJob with file_checks removed
    """
    # Create a copy of the verification job to avoid modifying the original
    from copy import deepcopy

    job_to_save = deepcopy(verification_job)

    # Remove file_checks from all files
    if job_to_save.files:
        for file in job_to_save.files:
            file.file_checks = []

    # Convert the verification job to a DynamoDB item
    job_item = model_to_dynamodb_item(job_to_save)

    # Save the job to DynamoDB
    verification_jobs_table.put_item(Item=job_item)

    print(f"Saved verification job {job_to_save.id} without file_checks")

    # Return the modified job (with empty file_checks)
    return job_to_save


# --- Helper Function to save job to DynamoDB ---
def save_verification_job_to_dynamodb(
    verification_job: VerificationJob,
) -> VerificationJob:
    """
    Saves a VerificationJob object to the DynamoDB table.

    Args:
        verification_job: The VerificationJob to save

    Returns:
        The VerificationJob that was saved
    """
    # Convert the verification job to a DynamoDB item
    job_item = model_to_dynamodb_item(verification_job)

    # Save the job to DynamoDB
    verification_jobs_table.put_item(Item=job_item)

    print(f"Saved verification job {verification_job.id} to DynamoDB")

    # Return the original job
    return verification_job


# --- Helper Function to Send Message to SQS Queue ---
# Note: This function now raises HTTPException directly for easier handling in route implementations
def queue_verification_job(job_id: str) -> str:
    """Sends a message to the SQS queue for the given job ID."""
    # Import HTTPException and status here as it's only used in this function within utils
    from fastapi import HTTPException, status
    from botocore.exceptions import ClientError

    try:
        message_body = json.dumps(
            {
                "verificationJobId": job_id,
                # Add other relevant info if needed by the processor
            }
        )

        # Send message to SQS queue
        sqs_response = sqs_client.send_message(
            QueueUrl=PROCESSING_QUEUE_URL,
            MessageBody=message_body,
            MessageAttributes={
                "JobType": {"DataType": "String", "StringValue": "verification"}
            },
        )
        # Return the message ID
        return str(sqs_response["MessageId"])
    except ClientError as e:
        print(f"AWS ClientError sending message to SQS for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue job for processing: {e.response['Error']['Message']}",
        ) from e
    except Exception as e:
        print(f"Unexpected error sending message to SQS for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while queueing the job: {str(e)}",
        ) from e
