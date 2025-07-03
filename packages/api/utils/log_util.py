import logging
import boto3
import uuid
from datetime import datetime, timezone
from schemas.datamodel import VerificationJobLogEntry
from constants import VERIFICATION_JOB_LOGS_TABLE_NAME
from utils.database import model_to_dynamodb_item

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize DynamoDB table resource
logs_table = None
if VERIFICATION_JOB_LOGS_TABLE_NAME:
    dynamodb = boto3.resource("dynamodb")
    logs_table = dynamodb.Table(VERIFICATION_JOB_LOGS_TABLE_NAME)
else:
    logger.warning(
        "VERIFICATION_JOB_LOGS_TABLE_NAME not set. Database logging disabled."
    )


def store_log_entry(job_id: str, level: int, message: str):
    """Creates and stores a VerificationJobLogEntry in DynamoDB."""
    if not logs_table:
        return

    if not job_id:
        level_name = logging._levelToName.get(level, f"Level {level}")
        logger.warning(
            f"Cannot store log entry without job_id. Message: {level_name} - {message}"
        )
        return

    try:
        log_entry = VerificationJobLogEntry(
            id=str(uuid.uuid4()),
            verification_job_id=job_id,
            timestamp=int(datetime.now(timezone.utc).timestamp()),
            level=logging._levelToName.get(level, f"Unknown Level {level}"),
            message=message,
        )
        log_item = model_to_dynamodb_item(log_entry)
        logs_table.put_item(Item=log_item)
    except Exception as e:
        logger.error(f"Failed to store log entry for job {job_id}: {e}")
