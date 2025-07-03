import asyncio
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Set
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
import boto3

# Import necessary models and utils from the verification_job_utils
from .verification_job_utils import (
    dynamodb_item_to_collection,
    verification_jobs_table,
    file_checks_table,
    dynamodb_item_to_verification_job,
    collections_table
)
from schemas.datamodel import (
    AssessmentStatus,
    Collection,
    VerificationJob,
    VerificationJobDto,
)

# Get the DynamoDB resource
# Ensure AWS credentials and region are configured (e.g., via environment variables)
dynamodb_resource = boto3.resource("dynamodb")


async def _batch_get_items(table_name: str, keys: List[Dict]) -> List[Dict]:
    """Helper function to perform batch_get_item requests."""
    if not keys:
        return []

    all_items = []
    key_batches = [
        keys[i : i + 100] for i in range(0, len(keys), 100)
    ]  # Chunk keys into batches of 100

    for key_batch in key_batches:
        current_batch_keys = key_batch
        items_in_batch = []
        max_retries = 5
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            if not current_batch_keys:
                break  # All keys in this batch processed or failed permanently

            try:
                request_items = {table_name: {"Keys": current_batch_keys}}
                response = dynamodb_resource.batch_get_item(RequestItems=request_items)

                fetched_items = response.get("Responses", {}).get(table_name, [])
                items_in_batch.extend(fetched_items)

                # Get unprocessed keys specifically for this batch attempt
                unprocessed_in_response = (
                    response.get("UnprocessedKeys", {})
                    .get(table_name, {})
                    .get("Keys", [])
                )
                current_batch_keys = (
                    unprocessed_in_response  # Set keys for the next retry attempt
                )

                if current_batch_keys:
                    print(
                        f"Unprocessed keys in batch for {table_name}: {len(current_batch_keys)}. Retrying attempt {attempt + 1}/{max_retries}..."
                    )
                    await asyncio.sleep(
                        retry_delay * (2**attempt)
                    )  # Exponential backoff
                else:
                    break  # All keys in this batch were processed in this attempt

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if error_code == "ProvisionedThroughputExceededException":
                    print(
                        f"Throttled fetching from {table_name}. Retrying attempt {attempt + 1}/{max_retries}..."
                    )
                    await asyncio.sleep(retry_delay * (2**attempt))
                elif error_code == "ResourceNotFoundException":
                    print(f"Error: Table {table_name} not found.")
                    raise  # Re-raise critical error
                else:
                    print(
                        f"ClientError during batch_get_item for {table_name} (batch attempt {attempt + 1}): {e}"
                    )
                    # Retry logic for other client errors within the batch attempt
                    if attempt == max_retries - 1:
                        print(
                            f"Warning: Failed to process batch for {table_name} due to ClientError after {max_retries} retries. Error: {e}"
                        )
                        # Decide whether to raise or just log and continue with the next batch
                        break  # Move to next batch or finish if this was the last attempt
                    await asyncio.sleep(retry_delay * (2**attempt))
            except Exception as e:
                print(
                    f"Unexpected error during batch_get_item for {table_name} (batch attempt {attempt + 1}): {e}"
                )
                if attempt == max_retries - 1:
                    print(
                        f"Warning: Failed to process batch for {table_name} due to unexpected error after {max_retries} retries. Error: {e}"
                    )
                    # Decide whether to raise or just log
                    break  # Move to next batch or finish
                await asyncio.sleep(retry_delay * (2**attempt))

        # After retries for a batch, check if keys remain unprocessed for this specific batch
        if current_batch_keys:
            print(
                f"Warning: Failed to fetch {len(current_batch_keys)} items from batch for {table_name} after {max_retries} retries."
            )
            # Log these specific keys if needed: print(f"Unprocessed keys: {current_batch_keys}")

        all_items.extend(
            items_in_batch
        )  # Add successfully fetched items from this batch

    # No top-level unprocessed_keys check needed as it's handled per batch
    # The warning about failed items is now printed within the batch loop

    return all_items


async def list_verification_jobs(
    filter_status: Optional[AssessmentStatus] = None,
    collection_id: Optional[str] = None,
    created_after: Optional[int] = None,
) -> List[VerificationJobDto]:
    """
    Optimized implementation to retrieve a list of verification jobs using batch operations.
    """
    try:
        # --- 1. Fetch Verification Jobs (Scan or Query) ---
        scan_kwargs = {}
        filter_expressions = []
        
        if filter_status:
            filter_expressions.append(Attr("status").eq(filter_status.value))
        if collection_id:
            if "KeyConditionExpression" not in scan_kwargs:
                filter_expressions.append(Attr("collection_id").eq(collection_id))
        if created_after:
            filter_expressions.append(Attr("created_at").gt(created_after))

        if filter_expressions:
            combined_filter = filter_expressions[0]
            for i in range(1, len(filter_expressions)):
                combined_filter = combined_filter & filter_expressions[i]
            scan_kwargs["FilterExpression"] = combined_filter

        verification_job_items = []
        # Use paginated scan (or query)
        paginator = verification_jobs_table.meta.client.get_paginator(
            "scan"
        )  # or 'query'
        page_iterator = paginator.paginate(
            TableName=verification_jobs_table.name, **scan_kwargs
        )
        for page in page_iterator:
            verification_job_items.extend(page.get("Items", []))

        if not verification_job_items:
            return []

        # --- 2. Convert to Models and Collect IDs for Batch Fetching ---
        verification_jobs: List[VerificationJob] = []
        collection_ids_to_fetch: Set[str] = set()
        file_check_keys_to_fetch: List[
            Dict
        ] = []  # List of key dicts for batch_get_item

        for item in verification_job_items:
            job = dynamodb_item_to_verification_job(item)
            verification_jobs.append(job)
            collection_ids_to_fetch.add(job.collection_id)
            if job.items:
                for item_instance in job.items:
                    file_check_keys_to_fetch.append(
                        {
                            "verification_job_id": job.id,
                            "item_instance_id": item_instance.id,
                        }
                    )

        collection_keys = [{"id": collection_id} for collection_id in collection_ids_to_fetch]

        # Run batch fetches in parallel
        collection_items_task = asyncio.create_task(
            _batch_get_items(collections_table.name, collection_keys)
        )
        file_check_items_task = asyncio.create_task(
            _batch_get_items(file_checks_table.name, file_check_keys_to_fetch)
        )

        collection_items, file_check_items = await asyncio.gather(
            collection_items_task, file_check_items_task
        )

        collection_map: Dict[str, Collection] = {}
        for collection_item in collection_items:
            try:
                ddb_collection = dynamodb_item_to_collection(collection_item)
                collection_map[ddb_collection.id] = ddb_collection
            except Exception as e:
                print(
                    f"Warning: Error processing collection item {collection_item.get('id', 'N/A')}: {e}"
                )

        # --- 6. Create DTOs ---
        dto_list: List[VerificationJobDto] = []
        for job in verification_jobs:
            collection = collection_map.get(job.collection_id)
            collection_name = collection.description if collection else None

            total_cost_val = float(job.cost) if job.cost else None

            # Create DTO
            dto = VerificationJobDto(
                **job.model_dump(),
                collection_name=collection_name,
                total_cost=total_cost_val,
            )
            dto_list.append(dto)

        return dto_list

    except ClientError as e:
        print(f"Error listing verification jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve verification jobs: {e.response['Error']['Message']}",
        ) from e
    except Exception as e:
        print(f"Unexpected error listing verification jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        ) from e
