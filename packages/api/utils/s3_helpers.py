import logging
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


def parse_decimal(value: Any) -> Any:
    """Recursively convert Decimal objects to float/int for JSON compatibility."""
    if isinstance(value, list):
        return [parse_decimal(v) for v in value]
    elif isinstance(value, dict):
        return {k: parse_decimal(v) for k, v in value.items()}
    elif isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        else:
            return float(value)
    return value


def generate_presigned_urls_for_job_files(
    verification_job_id: str,
    s3_client,
    verification_jobs_table,
    storage_bucket_name: str,
    expires_in: int = 3600,
) -> dict[str, str]:
    """Retrieves a verification job and generates presigned GET URLs for its files."""
    presigned_urls = {}
    logger.info(f"Generating presigned URLs for job: {verification_job_id}")

    try:
        response = verification_jobs_table.get_item(Key={"id": verification_job_id})
        item = response.get("Item")
        if not item:
            logger.warning(f"Verification job {verification_job_id} not found")
            return {}

        files_list = item.get("files", [])
        if not isinstance(files_list, list) or not files_list:
            return {}

        for file_data in files_list:
            if not isinstance(file_data, dict):
                continue

            file_id = file_data.get("id")
            s3_key = file_data.get("s3_key")

            if not file_id:
                continue

            if s3_key:
                try:
                    url = s3_client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": storage_bucket_name, "Key": s3_key},
                        ExpiresIn=expires_in,
                    )
                    presigned_urls[file_id] = url
                except ClientError:
                    logger.warning(f"Error generating URL for file {file_id}")
                except Exception:
                    logger.error(f"Unexpected error for file {file_id}")

    except ClientError:
        logger.error(f"DynamoDB error fetching job {verification_job_id}")
        return {}
    except Exception:
        logger.error(f"Unexpected error for job {verification_job_id}")
        return {}

    return presigned_urls
