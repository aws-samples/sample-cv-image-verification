import os
from typing import Optional
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

STORAGE_BUCKET_NAME = os.getenv("STORAGE_BUCKET_NAME", "my-bucket")
EXPORT_BUCKET_NAME  = os.getenv("EXPORT_BUCKET_NAME", "export-bucket")
VERIFICATION_JOBS_TABLE_NAME = os.getenv(
    "VERIFICATION_JOBS_TABLE_NAME", "verification-jobs"
)
ITEMS_TABLE_NAME = os.getenv("ITEMS_TABLE_NAME", "items")
COLLECTIONS_TABLE_NAME = os.getenv("COLLECTIONS_TABLE_NAME", "collections")
AGENTS_TABLE_NAME = os.getenv("AGENTS_TABLE_NAME", "agents")
PROCESSING_QUEUE_URL = os.getenv("PROCESSING_QUEUE_URL", "PROCESSING_QUEUE_URL")
LOCATION_INDEX_NAME = os.getenv("LOCATION_INDEX_NAME", "location-index")
VERIFICATION_JOB_LOGS_TABLE_NAME = os.getenv(
    "VERIFICATION_JOB_LOGS_TABLE_NAME", "verification-job-logs"
)
FILE_CHECKS_TABLE_NAME = os.getenv("FILE_CHECKS_TABLE_NAME", "file-checks")
LLM_CONFIG_TABLE_NAME = os.getenv("LLM_CONFIG_TABLE_NAME", "llm-config")

# The maximum distance (in kilometers) for address matching
MAX_ADDRESS_DISTANCE = os.getenv("MAX_ADDRESS_DISTANCE", 0.5)  # in kms

BEDROCK_ROLE_ARN_PARAMETER = os.getenv("BEDROCK_ROLE_ARN_PARAMETER")

AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")
TAVILY_API_KEY_SECRET = os.getenv("TAVILY_API_KEY_SECRET", "TAVILY_API_KEY_SECRET")


def get_bedrock_role_arn()-> Optional[str]:
    """
    Retrieve the Bedrock role ARN from SSM Parameter Store.
    
    Returns:
        str: The Bedrock role ARN if found, None otherwise.
    """
    if not BEDROCK_ROLE_ARN_PARAMETER:
        return None
    
    try:
        ssm_client = boto3.client('ssm')
        response = ssm_client.get_parameter(
            Name=BEDROCK_ROLE_ARN_PARAMETER,
            WithDecryption=True
        )
        param_value = response['Parameter']['Value']
        if len(param_value) > 0 and param_value.lower()!='na':
            return param_value
        return None
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'ParameterNotFound':
            return None
        raise e
    except Exception:
        return None
