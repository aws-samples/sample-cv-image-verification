import asyncio
from datetime import datetime, timezone
import json
from logging import INFO
import os
import boto3
from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import DynamoDBServiceResource
from utils.log_util import store_log_entry
from utils.config_helpers import get_verification_job_second_pass
from utils.llm import calculate_llm_pricing
from routers.methods.verification_job_utils import (
    fetch_verification_job,
    save_verification_job_to_dynamodb,
)
from schemas.datamodel import AssessmentStatus, ItemInstance, CollectionFileInstance
from item_processing.item_processor import (
    CallUsingAllFilesResponse,
    call_using_all_files,
    call_second_pass_verification,
)
from item_processing.aws_helpers import get_image_bytes_from_s3, detect_labels_s3
from constants import STORAGE_BUCKET_NAME

# Initialize DynamoDB client
dynamodb: DynamoDBServiceResource = boto3.resource("dynamodb")
verification_jobs_table = dynamodb.Table(os.environ["VERIFICATION_JOBS_TABLE_NAME"])


async def verify_image_file(file: CollectionFileInstance) -> bool:
    """Verifies if the file is a JPEG or PNG image"""
    allowed_types = ["image/jpeg", "image/png", "image/jpg"]
    return file.content_type.lower() in allowed_types


async def perform_second_pass_verification(
    verification_job_files: list[CollectionFileInstance], item_instance: ItemInstance
) -> CallUsingAllFilesResponse:
    """Perform second pass verification on the files"""

    print(f"Performing second pass verification on {len(verification_job_files)} files")

    # Convert the list of files to a list of dict containing id and s3_key
    verification_job_files_dict = [
        {"id": file.id, "s3_key": file.s3_key} for file in verification_job_files
    ]

    joined_description = " ".join(
        [d.description for d in item_instance.description_filtering_rules_applied]
    )
    item_info = f"Item ID: {item_instance.id}, Item Description: {joined_description}"
    response = await call_second_pass_verification(
        item_info, verification_job_files_dict
    )
    print(f"Second pass verification response: {response}")
    return response


async def async_handler(event):
    # Parse the event payload
    if isinstance(event, str):
        payload = json.loads(event)
    elif "body" in event and isinstance(event["body"], str):
        payload = json.loads(event["body"])
    else:
        payload = event

    verification_job_id = payload.get("verificationJobId")
    if not verification_job_id:
        raise ValueError("Missing verificationJobId in payload")

    store_log_entry(verification_job_id, INFO, "Starting verification job processing")

    current_timestamp = int(datetime.now(timezone.utc).timestamp())
    
    # Fetch the verification job with all associated data
    verification_job, _ = fetch_verification_job(verification_job_id)
    
    try:
        verification_job.status = AssessmentStatus.ASSESSING
        verification_job.updated_at = current_timestamp
        save_verification_job_to_dynamodb(verification_job)
        

        # Get Items and files from the verification job
        item_instances = getattr(verification_job, "items", [])
        verification_job_files = getattr(verification_job, "files", [])

        # Track processed files to avoid duplicates
        processed_file_hashes = set()
        files_to_remove = []

        # Labels to check for in the images
        # Get all image labels to check from Item instances
        labels_to_check = []

        store_log_entry(verification_job_id, INFO, "Checking for labelling rules")

        for item in item_instances:
            if (
                hasattr(item, "label_filtering_rules_applied")
                and item.label_filtering_rules_applied
            ):
                for rule in item.label_filtering_rules_applied:
                    if hasattr(rule, "image_labels"):
                        # Add individual labels from each rule
                        if isinstance(rule.image_labels, list):
                            labels_to_check.extend(rule.image_labels)
                        else:
                            labels_to_check.append(rule.image_labels)

        # Convert all labels to lowercase for case-insensitive comparison
        labels_to_check = list(set([label.lower() for label in labels_to_check if label]))

        store_log_entry(
            verification_job_id, INFO, f"{len(labels_to_check)} labels to check"
        )

        # Process each file in verification_job_files
        for veri_job_file in verification_job_files:
            s3_bucket = STORAGE_BUCKET_NAME

            is_image = await verify_image_file(veri_job_file)

            if not is_image:
                store_log_entry(
                    verification_job_id,
                    INFO,
                    f"File {veri_job_file.s3_key} is not an image, ignoring it",
                )

                files_to_remove.append(veri_job_file)
                continue

            # Load the file from S3
            file_bytes = await get_image_bytes_from_s3(s3_bucket, veri_job_file.s3_key)

            # Skip if file_bytes is None
            if file_bytes is None:
                store_log_entry(
                    verification_job_id,
                    INFO,
                    f"Could not load file {veri_job_file.s3_key}, skipping",
                )
                files_to_remove.append(veri_job_file)
                continue

            # Use the file content hash to check for duplicates
            file_hash = hash(file_bytes)
            if file_hash in processed_file_hashes:
                files_to_remove.append(veri_job_file)
                store_log_entry(
                    verification_job_id,
                    INFO,
                    f"Removing duplicate file {veri_job_file.s3_key}",
                )
                continue

            # Add to processed files
            processed_file_hashes.add(file_hash)

            # Check if it has specific labels using Rekognition
            labels = await detect_labels_s3(image_bytes=file_bytes,resize_image=True)

            # Check if any of the labels we're looking for are present
            for label in labels:
                if (
                    label.get("Name", "").lower() in labels_to_check
                    and label.get("Confidence", 0) > 70
                ):
                    files_to_remove.append(veri_job_file)
                    store_log_entry(
                        verification_job_id,
                        INFO,
                        f"Removing {veri_job_file.s3_key} due to label match: {label.get('Name')}",
                    )

                    break

        # Remove files that were flagged
        if files_to_remove:
            verification_job_files = [
                f for f in verification_job_files if f not in files_to_remove
            ]

        # Process the verification job
        
        # Group Items by cluster number
        cluster_groups = {}
        standalone_items = []
        
        for item in item_instances:
            if item.cluster_number is not None:
                if item.cluster_number not in cluster_groups:
                    cluster_groups[item.cluster_number] = []
                cluster_groups[item.cluster_number].append(item)
            else:
                standalone_items.append(item)
        
        # Prepare the final list of Items to process
        items_to_process = standalone_items.copy()  # Include all standalone Items
        
        store_log_entry(
                verification_job_id,
                INFO,
                f"Including {len(items_to_process)} standalone Items for processing"
            )
        
        # For clustered Items, only include them if ALL Items in the cluster are present
        for cluster_number, items in cluster_groups.items():
            # Check if all Items in the cluster are present in the verification job
            all_items_in_cluster = {item.id for item in items}
            items_in_job = {item.id for item in verification_job.items if item.cluster_number == cluster_number}
            
            # Only include the cluster if all Items in the cluster are in the job
            if all_items_in_cluster.issubset(items_in_job):
                items_to_process.extend(items)
            
            store_log_entry(
                verification_job_id,
                INFO,
                f"Cluster {cluster_number}: Including {len(items)} Items in processing"
            )
        
        store_log_entry(
            verification_job_id, 
            INFO, 
            f"Processing {len(items_to_process)} Items after cluster filtering (from original {len(item_instances)})"
        )
        start_time = datetime.now(timezone.utc)
        store_log_entry(
            verification_job_id, 
            INFO, 
            f"Calling LLM with {len(verification_job_files)} files for {len(items_to_process)} Items"
        )
        
        results, token_usage, positions = await call_using_all_files(job=verification_job,
            item_instances=items_to_process, collection_files=verification_job_files
        )
        
        end_time = datetime.now(timezone.utc)
        store_log_entry( 
            verification_job_id,
            INFO,
            f"LLM call completed in {end_time - start_time} seconds with {len(results.items)} results",
        )

        # Validate that LLM results only contain Item IDs from the original job
        original_item_ids = {item.id for item in verification_job.items}
        result_item_ids = {result_item.item_id for result_item in results.items}
        unexpected_item_ids = result_item_ids - original_item_ids
        if unexpected_item_ids:
            raise ValueError(
                f"LLM results contain unexpected item_ids not found in the verification job: {unexpected_item_ids}"
            )

        # Calculate cost based on token usage
        input_tokens = getattr(token_usage, "input_tokens", 0)
        output_tokens = getattr(token_usage, "output_tokens", 0)

        # Process results and update Item statuses
        any_cluster_passed = False  # Track if any cluster passes
        all_mandatory_standalone_passed = True  # Track if all mandatory standalone Items pass
        current_timestamp = int(datetime.now(timezone.utc).timestamp())

        # Group Items by cluster for evaluation
        item_clusters = {}
        standalone_items_final = []

        # First pass: Group Items and determine if LLM found matches
        for item in verification_job.items:
            item.updated_at = current_timestamp
            
            # Explicitly preserve the cluster_number
            if hasattr(item, 'cluster_number'):
                if item.cluster_number is not None:
                    if item.cluster_number not in item_clusters:
                        item_clusters[item.cluster_number] = []
                    item_clusters[item.cluster_number].append(item)
                else:
                    standalone_items_final.append(item)
            else:
                standalone_items_final.append(item)

            # Find matched Item in results
            matched_item = next(
                (r for r in results.items if r.item_id == item.id),
                None,
            )

            # Assign confidence and reasoning if a match was found
            if matched_item:
                item.confidence = matched_item.confidence
                item.assessment_reasoning = matched_item.reasoning
                
                # Find matching files only if image was found
                if matched_item.image_found and (matched_item.confidence is not None and matched_item.confidence >= 0.8):
                    file_ids = [positions[file] for file in matched_item.file_ids]
                    matched_files = [
                        file for file in verification_job.files if file.id in file_ids
                    ]
                    item.approved_files = matched_files
                else:
                    item.approved_files = []
            else:
                item.confidence = None
                item.assessment_reasoning = None
                item.approved_files = []

        items_to_save = []
        
        # Process standalone Items (no cluster)
        for item in standalone_items_final:
            matched_item = next(
                (r for r in results.items if r.item_id == item.id),
                None,
            )
            
            # Check if the Item has any mandatory description filtering rules
            has_mandatory_rule = any(
                rule.mandatory for rule in item.description_filtering_rules_applied 
                if hasattr(rule, 'mandatory')
            )
            
        
            # If there are mandatory rules, check if the LLM found a match
            if (
                matched_item is None
                or not matched_item.image_found
                or (matched_item.confidence is not None and matched_item.confidence < 0.8)
                or len(getattr(item, "approved_files", [])) == 0
            ):
                if has_mandatory_rule:
                    # If a mandatory standalone Item fails, mark it
                    all_mandatory_standalone_passed = False
                item.status = AssessmentStatus.REJECTED
            else:
                # Do we need a second pass verification?
                matched_files = item.approved_files
                if matched_files and get_verification_job_second_pass():
                    print("Performing second pass verification")
                    sp_results = await perform_second_pass_verification(
                        matched_files, item
                    )
                    sp_matched_item = [
                        r for r in sp_results.response.items if r.item_id == item.id
                    ]

                    # Make sure at least one file is matched
                    if sp_matched_item and any(
                        item.image_found for item in sp_matched_item
                    ):
                        item.status = AssessmentStatus.APPROVED
                        item.assessment_reasoning = " ".join(
                            [
                                j.reasoning
                                for j in [x for x in sp_matched_item if x.image_found]
                            ]
                        )
                    else:
                        # Update our flag if a mandatory standalone Item fails second pass
                        if has_mandatory_rule:
                            all_mandatory_standalone_passed = False
                        item.assessment_reasoning = " ".join(
                            [
                                j.reasoning
                                for j in [
                                    x for x in sp_matched_item if not x.image_found
                                ]
                            ]
                        )
                        item.status = AssessmentStatus.REJECTED
                    input_tokens += sp_results.token_usage.input_tokens
                    output_tokens += sp_results.token_usage.output_tokens
                else:
                    print("No second pass verification required.")
                    item.status = AssessmentStatus.APPROVED
            
            items_to_save.append(item)
        
        # Process clustered Items
        for cluster_num, items in item_clusters.items():
            store_log_entry(
                verification_job_id,
                INFO,
                f"Processing cluster {cluster_num} with {len(items)} Items"
            )
            
            # If there are mandatory rules, check if any Item in the cluster fails
            any_mandatory_failed = False
            for item in items:
                matched_item = next(
                    (r for r in results.items if r.item_id == item.id),
                    None,
                )
                
                matched_files = item.approved_files
                
                has_mandatory_rule = any(
                    rule.mandatory for rule in item.description_filtering_rules_applied 
                        if hasattr(rule, 'mandatory')
                    )
                
                # Check if Item would fail based on first-pass checks
                if (
                    matched_item is None
                    or not matched_item.image_found
                    or (matched_item.confidence is not None and matched_item.confidence < 0.8)
                    or len(matched_files) == 0
                ):
                    item.status = AssessmentStatus.REJECTED
                    store_log_entry(
                        verification_job_id,
                        INFO,
                        f"Item {item.id} in cluster {cluster_num} rejected due to cluster rule"
                    )
                    if has_mandatory_rule:
                        any_mandatory_failed = True
                else:
                    item.status = AssessmentStatus.APPROVED
                    
                # Check second pass verification if needed
                if matched_files and get_verification_job_second_pass():
                    sp_results = await perform_second_pass_verification(
                        matched_files, item
                    )
                    sp_matched_item = [
                        r for r in sp_results.response.items if r.item_id == item.id
                    ]
                    
                    # If second pass verification fails, mark as failed
                    if not (sp_matched_item and any(item.image_found for item in sp_matched_item)):
                        any_failed = True
                        break
                        
                    input_tokens += sp_results.token_usage.input_tokens
                    output_tokens += sp_results.token_usage.output_tokens
            
            # Apply the result to all Items in the cluster
            for item in items:
                if not any_mandatory_failed:
                    # The cluster passed, mark it for the overall job status
                    any_cluster_passed = True
                    store_log_entry(
                        verification_job_id,
                        INFO,
                        f"Item {item.id} in cluster {cluster_num} approved"
                    )
                items_to_save.append(item)

        cost = calculate_llm_pricing(input_tokens, output_tokens)

        verification_job.items = items_to_save

        # Update verification job status based on results:
        # Job passes if (Any cluster passes) AND (All mandatory standalone Items pass)
        verification_job.status = (
            AssessmentStatus.APPROVED if (any_cluster_passed or not item_clusters) and all_mandatory_standalone_passed 
            else AssessmentStatus.REJECTED
        )
        
        store_log_entry(
            verification_job_id,
            INFO,
            f"Final status: {verification_job.status} (any_cluster_passed={any_cluster_passed}, all_mandatory_standalone_passed={all_mandatory_standalone_passed})"
        )

        verification_job.updated_at = current_timestamp
        verification_job.cost = cost

        # Save the updated verification job
        save_verification_job_to_dynamodb(verification_job)
        store_log_entry(
            verification_job_id,
            INFO,
            f"Job {verification_job_id} processed successfully with status {verification_job.status}",
        )
    except Exception as e:
        store_log_entry(
            verification_job_id,
            INFO,
            f"Error processing job {verification_job_id}: {str(e)}",
        )
        # Update the job status to ERROR
        verification_job.status = AssessmentStatus.ERROR
        verification_job.updated_at = current_timestamp
        save_verification_job_to_dynamodb(verification_job)
        raise e


def handler(event, context):
    """AWS Lambda handler for verification job processing"""
    for record in event.get("Records", []):
        if "body" in record and isinstance(record["body"], str):
            body = json.loads(record["body"])
            asyncio.get_event_loop().run_until_complete(async_handler(body))

if __name__ == "__main__":
    test_event = {
        "Records": [{"body": '{"verificationJobId": "Uxi27rpPyA8fxzk73pcDAY"}'}]
    }
    handler(test_event, {})
