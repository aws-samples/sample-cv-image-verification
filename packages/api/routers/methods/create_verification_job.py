import time
from fastapi import HTTPException, status
from botocore.exceptions import ClientError
import shortuuid

# Import necessary models and utils from the verification_job_utils
from .verification_job_utils import (
    verification_jobs_table,
    collections_table,
    dynamodb_item_to_collection,
    model_to_dynamodb_item,
    queue_verification_job,  # Import the helper
)

# STORAGE_BUCKET_NAME is used within _create_file_instances, no need to import here unless used elsewhere
from schemas.datamodel import (
    VerificationJob,
    AssessmentStatus,
)
from schemas.requests_responses import (
    CreateVerificationJobRequest,
    CreateVerificationJobResponse,
)


async def create_verification_job(
    job_request: CreateVerificationJobRequest,
) -> CreateVerificationJobResponse:
    """
    Implementation to create a new verification job, deriving Item instances from the specified collection,
    and starts the processing workflow.
    """
    current_time = int(time.time())
    job_id = None

    try:
        # 1. Fetch the Collection
        try:
            col_response = collections_table.get_item(
                Key={"id": job_request.collection_id}
            )
            collection_item = col_response.get("Item")
            if not collection_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Collection with ID {job_request.collection_id} not found",
                )
            collection = dynamodb_item_to_collection(collection_item)
        except ClientError as e:
            print(f"Error fetching collection {job_request.collection_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve collection: {e.response['Error']['Message']}",
            ) from e

        # Generate a unique job ID, ensuring it doesn't already exist
        while True:
            job_id = str(shortuuid.uuid())
            try:
                # Check if the ID already exists in the table
                response = verification_jobs_table.get_item(
                    Key={"id": job_id},
                    ProjectionExpression="id",  # Only need to check existence, not fetch full item
                )
                if "Item" not in response:
                    # ID is unique, break the loop
                    break
                # If Item exists, the loop continues to generate a new ID
                print(f"Job ID {job_id} already exists, generating a new one.")
            except ClientError as e:
                print(f"Error checking job ID {job_id} existence: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to verify job ID uniqueness: {e.response['Error']['Message']}",
                ) from e

        # 2. Create ItemInstance objects from the collection's items
        from schemas.datamodel import ItemInstance
        item_instances = []
        if collection.items:
            for item in collection.items:
                item_instance = ItemInstance(
                    id=str(shortuuid.uuid()),
                    created_at=current_time,
                    updated_at=current_time,
                    name=item.name,
                    description=item.description,
                    label_filtering_rules_applied=item.label_filtering_rules,
                    description_filtering_rules_applied=item.description_filtering_rules,
                    status=AssessmentStatus.PENDING,
                    address=collection.address,
                    item_id=item.id,  # Keep reference to original item
                    cluster_number=item.cluster_number,
                    agent_ids=item.agent_ids or [],
                
                )
                item_instances.append(item_instance)

        # 3. Create CollectionFileInstance objects from the collection's files
        from schemas.datamodel import CollectionFileInstance
        file_instances = []
        if collection.files:
            for file in collection.files:
                file_instance = CollectionFileInstance(
                    id=file.id,
                    created_at=file.created_at,
                    s3_key=file.s3_key,
                    description=file.description,
                    content_type=file.content_type,
                    filename=file.filename,
                    size=file.size,
                    file_checks=[]
                )
                file_instances.append(file_instance)

        # 4. Create the initial VerificationJob object
        verification_job = VerificationJob(
            id=job_id,
            created_at=current_time,
            updated_at=current_time,
            collection_id=job_request.collection_id,
            status=job_request.status or AssessmentStatus.PENDING,
            confidence=job_request.confidence,
            items=item_instances,
            files=file_instances,
            search_internet=job_request.search_internet,
        )

        # 5. Save initial job data to DynamoDB
        item_data = model_to_dynamodb_item(verification_job)
        verification_jobs_table.put_item(Item=item_data)

        # 6. Queue the job for processing
        queue_verification_job(job_id)

        # 7. Update job status after queuing
        verification_job.updated_at = int(time.time())
        updated_item_data = model_to_dynamodb_item(verification_job)
        verification_jobs_table.put_item(Item=updated_item_data)

        return CreateVerificationJobResponse(verification_job=verification_job)

    except HTTPException as e:  # Re-raise 404 or other HTTP errors
        raise e
    except ClientError as e:
        error_source = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        print(
            f"AWS ClientError ({error_source}) creating verification job {job_id or 'unknown'}: {error_message}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save verification job: {error_message}",
        ) from e
    except Exception as e:
        print(f"Unexpected error creating verification job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
