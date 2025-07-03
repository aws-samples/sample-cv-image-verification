import time
import boto3
from decimal import Decimal
from typing import Dict, Optional, Any, cast, List
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from pydantic import BaseModel
from enum import Enum

from schemas.datamodel import (
    VerificationJob,
    Collection,
    CollectionFileItemInstance,
    AssessmentStatus,
)

from .conversion import dynamodb_item_to_pydantic
from constants import (
    VERIFICATION_JOBS_TABLE_NAME,
    COLLECTIONS_TABLE_NAME,
    FILE_CHECKS_TABLE_NAME,
    AWS_REGION,
)

# Initialize AWS resource abstraction layer
dynamodb_resource = boto3.resource("dynamodb", region_name=AWS_REGION)

# Initialize DynamoDB Table References
verification_jobs_table_name = VERIFICATION_JOBS_TABLE_NAME
collections_table_name = COLLECTIONS_TABLE_NAME
file_checks_table_name = FILE_CHECKS_TABLE_NAME


def _convert_value_for_dynamodb(value: Any) -> Any:
    """Recursively converts Python types to DynamoDB compatible types."""
    if isinstance(value, list):
        return [_convert_value_for_dynamodb(item) for item in value]
    elif isinstance(value, dict):
        return {k: _convert_value_for_dynamodb(v) for k, v in value.items()}
    elif isinstance(value, float):
        return Decimal(str(value))
    elif isinstance(value, Enum):
        return value.value
    else:
        return value


def model_to_dynamodb_item(model_instance: BaseModel) -> Dict[str, Any]:
    """Converts a Pydantic model instance to a DynamoDB-compatible dictionary."""
    if not isinstance(model_instance, BaseModel):
        raise TypeError("Input must be a Pydantic BaseModel instance.")

    obj_dict = model_instance.model_dump(mode="json", exclude_none=True)
    return cast(Dict[str, Any], _convert_value_for_dynamodb(obj_dict))


async def fetch_verification_job(verification_job_id: str) -> Optional[VerificationJob]:
    """Fetches the entire VerificationJob object from DynamoDB and enriches it with file_checks."""
    response = dynamodb_resource.Table(verification_jobs_table_name).get_item(
        Key={"id": verification_job_id}
    )
    item = response.get("Item")
    if not item:
        return None

    job_base = dynamodb_item_to_pydantic(item, VerificationJob)
    if not job_base:
        return None

    job = cast(VerificationJob, job_base)

    if job.items and job.files:
        item_instance_ids = [item.id for item in job.items]

        for item_instance_id in item_instance_ids:
            try:
                file_checks_list = await fetch_file_checks(
                    verification_job_id, item_instance_id
                )

                file_checks_by_file_id: Any = {}
                for check in file_checks_list:
                    file_id = check.get("file_instance_id")
                    if file_id:
                        if file_id not in file_checks_by_file_id:
                            file_checks_by_file_id[file_id] = []
                        file_checks_by_file_id[file_id].append(check)

                for file in job.files:
                    if file.id in file_checks_by_file_id:
                        checks_for_file = []
                        for check_data in file_checks_by_file_id[file.id]:
                            parsed_check = dynamodb_item_to_pydantic(
                                check_data, CollectionFileItemInstance
                            )
                            if parsed_check:
                                checks_for_file.append(parsed_check)

                        if hasattr(file, "file_checks"):
                            file.file_checks.extend(checks_for_file)
                        else:
                            file.file_checks = checks_for_file

            except Exception:
                pass

    return job


async def fetch_collection(collection_id: str) -> Optional[Collection]:
    """Fetches the entire Collection object from DynamoDB."""
    response = dynamodb_resource.Table(collections_table_name).get_item(
        Key={"id": collection_id}
    )
    item = response.get("Item")
    if item:
        collection_base = dynamodb_item_to_pydantic(item, Collection)
        if collection_base:
            collection = cast(Collection, collection_base)
            return collection
    return None


async def update_item_instance_status(
    verification_job_id: str,
    item_instance_id: str,
    status: str,
    reasoning: Optional[str] = None,
    confidence: Optional[float] = None,
    approved_collection_files: Optional[List[CollectionFileItemInstance]] = None,
):
    """Updates the status, reasoning, and confidence of an ItemInstance within its VerificationJob."""
    instance_index = -1

    response = dynamodb_resource.Table(verification_jobs_table_name).get_item(
        Key={"id": verification_job_id}, ProjectionExpression="items"
    )
    job_item = response.get("Item")
    if not job_item or "items" not in job_item or not isinstance(job_item["items"], list):
        raise ValueError(
            f"VerificationJob {verification_job_id} or 'items' list not found."
        )

    items_list = job_item["items"]
    for i, instance_item in enumerate(items_list):
        if (
            isinstance(instance_item, dict)
            and instance_item.get("id") == item_instance_id
        ):
            instance_index = i
            break

    update_expression_parts_set = []
    update_expression_parts_remove = []
    expression_attribute_values: Dict[str, Any] = {}

    current_time = int(time.time())
    expression_attribute_names = {
        "#status_field": "status",
        "#reasoning_field": "assessment_reasoning",
        "#confidence_field": "confidence",
        "#updated_at_field": "updated_at",
    }

    update_expression_parts_set.append(
        f"items[{instance_index}].#updated_at_field = :updated_at"
    )
    expression_attribute_values[":updated_at"] = current_time

    try:
        valid_status_enum = AssessmentStatus(status)
        valid_status_value = valid_status_enum.value
    except ValueError:
        raise ValueError(f"Invalid status value provided: {status}") from None

    update_expression_parts_set.append(
        f"items[{instance_index}].#status_field = :status"
    )
    expression_attribute_values[":status"] = cast(Any, valid_status_value)

    if reasoning is not None:
        update_expression_parts_set.append(
            f"items[{instance_index}].#reasoning_field = :reasoning"
        )
        expression_attribute_values[":reasoning"] = reasoning
    else:
        update_expression_parts_remove.append(
            f"items[{instance_index}].#reasoning_field"
        )

    if confidence is not None:
        update_expression_parts_set.append(
            f"items[{instance_index}].#confidence_field = :confidence"
        )
        expression_attribute_values[":confidence"] = cast(Any, Decimal(str(confidence)))
    else:
        update_expression_parts_remove.append(
            f"items[{instance_index}].#confidence_field"
        )

    expression_attribute_names["#approved_files_field"] = "approved_work_order_files"

    if approved_collection_files is not None:
        update_expression_parts_set.append(
            f"items[{instance_index}].#approved_files_field = :approved_files"
        )
        expression_attribute_values[":approved_files"] = cast(
            Any,
            _convert_value_for_dynamodb(
                [f.model_dump(mode="json") for f in approved_collection_files]
            ),
        )
    else:
        update_expression_parts_remove.append(
            f"items[{instance_index}].#approved_files_field"
        )

    set_clause = (
        "SET " + ", ".join(update_expression_parts_set)
        if update_expression_parts_set
        else ""
    )
    remove_clause = (
        "REMOVE " + ", ".join(update_expression_parts_remove)
        if update_expression_parts_remove
        else ""
    )
    update_expression = f"{set_clause} {remove_clause}".strip()

    if not update_expression or not set_clause:
        return True

    try:
        response = dynamodb_resource.Table(verification_jobs_table_name).update_item(
            Key={"id": verification_job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ExpressionAttributeNames=expression_attribute_names,
            ReturnValues="UPDATED_NEW",
            ConditionExpression=Attr("id").exists(),
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError(
                f"VerificationJob {verification_job_id} disappeared before update."
            ) from None
        raise


async def fetch_file_checks(
    verification_job_id: str, item_instance_id: str
) -> List[Dict[str, Any]]:
    """Fetches file checks for a given verification job and Item instance."""
    try:
        response = dynamodb_resource.Table(file_checks_table_name).get_item(
            Key={
                "verification_job_id": verification_job_id,
                "item_instance_id": item_instance_id,
            }
        )

        item = response.get("Item")
        if item and "file_checks" in item and isinstance(item["file_checks"], list):
            return item["file_checks"]
        return []
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return []
        raise


async def append_collection_file_item_instance(
    verification_job_id: str,
    file_instance_id: str,
    item_check_instance: CollectionFileItemInstance,
):
    """Adds a CollectionFileItemInstance to the dedicated file_checks table."""
    response = dynamodb_resource.Table(verification_jobs_table_name).get_item(
        Key={"id": verification_job_id},
        ProjectionExpression="files",
    )
    job_item = response.get("Item")
    if (
        not job_item
        or "files" not in job_item
        or not isinstance(job_item["files"], list)
    ):
        raise ValueError(
            f"VerificationJob {verification_job_id} or 'files' list not found."
        )

    file_exists = False
    files_list = job_item["files"]
    for instance_item in files_list:
        if (
            isinstance(instance_item, dict)
            and instance_item.get("id") == file_instance_id
        ):
            file_exists = True
            break

    if not file_exists:
        raise ValueError(
            f"CollectionFileInstance {file_instance_id} not found in job {verification_job_id}."
        )

    item_check_item = model_to_dynamodb_item(item_check_instance)
    item_check_item["file_instance_id"] = file_instance_id
    current_time = int(time.time())

    response = dynamodb_resource.Table(file_checks_table_name).get_item(
        Key={
            "verification_job_id": verification_job_id,
            "item_instance_id": item_check_instance.item_instance_id,
        }
    )

    item = response.get("Item")
    if item:
        update_expression = "SET #fc = list_append(if_not_exists(#fc, :empty_list), :new_check), updated_at = :updated_at"
        expression_attribute_names = {"#fc": "file_checks"}
        expression_attribute_values = {
            ":new_check": [item_check_item],
            ":empty_list": [],
            ":updated_at": current_time,
        }

        dynamodb_resource.Table(file_checks_table_name).update_item(
            Key={
                "verification_job_id": verification_job_id,
                "item_instance_id": item_check_instance.item_instance_id,
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="UPDATED_NEW",
        )
    else:
        file_checks_record = {
            "verification_job_id": verification_job_id,
            "item_instance_id": item_check_instance.item_instance_id,
            "created_at": current_time,
            "updated_at": current_time,
            "file_checks": [item_check_item],
        }

        dynamodb_resource.Table(file_checks_table_name).put_item(
            Item=file_checks_record
        )

    return True


async def update_file_check(
    verification_job_id: str,
    item_instance_id: str,
    file_instance_id: str,
    update_data: Dict[str, Any],
):
    """Updates a specific file check in the file_checks table."""
    response = dynamodb_resource.Table(file_checks_table_name).get_item(
        Key={
            "verification_job_id": verification_job_id,
            "item_instance_id": item_instance_id,
        }
    )

    item = response.get("Item")
    if (
        not item
        or "file_checks" not in item
        or not isinstance(item["file_checks"], list)
    ):
        raise ValueError(
            f"No file_checks found for verification job {verification_job_id} and Item instance {item_instance_id}"
        )

    file_check_index = -1
    for i, check in enumerate(item["file_checks"]):
        if check.get("file_instance_id") == file_instance_id:
            file_check_index = i
            break

    if file_check_index == -1:
        raise ValueError(f"File check for file instance {file_instance_id} not found")

    update_expression_parts = ["SET updated_at = :updated_at"]
    expression_attribute_values = {":updated_at": int(time.time())}
    expression_attribute_names: Any = {}

    for key, value in update_data.items():
        if key not in ["verification_job_id", "item_instance_id"]:
            attribute_path = f"file_checks[{file_check_index}].{key}"
            update_expression_parts.append(f"{attribute_path} = :val_{key}")
            expression_attribute_values[f":val_{key}"] = _convert_value_for_dynamodb(
                value
            )

    update_expression = " , ".join(update_expression_parts)

    try:
        dynamodb_resource.Table(file_checks_table_name).update_item(
            Key={
                "verification_job_id": verification_job_id,
                "item_instance_id": item_instance_id,
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ExpressionAttributeNames=expression_attribute_names
            if expression_attribute_names
            else None,
            ConditionExpression="attribute_exists(verification_job_id) AND attribute_exists(item_instance_id)",
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ValueError(
                f"File check record not found for verification job {verification_job_id} and Item instance {item_instance_id}"
            ) from e
        raise
