

from tempfile import TemporaryFile
from io import BytesIO
import time
import asyncio
from constants import EXPORT_BUCKET_NAME
from routers.methods.list_verification_jobs import list_verification_jobs
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError


def upload_to_s3(file, key):
    
    s3 = boto3.client('s3')
    
    try:
        s3.upload_fileobj(file, EXPORT_BUCKET_NAME, key)
        print(f"File uploaded to S3 bucket '{EXPORT_BUCKET_NAME}' with key '{key}'")
    except (NoCredentialsError, PartialCredentialsError) as e:
        print(f"Failed to upload file to S3: {e}")
    except Exception as e:
        print(f"An error occurred while uploading to S3: {e}")
    
def handler(event, context):
    """
    AWS Lambda handler for exporting verification jobs data to a CSV file in S3.
    This function retrieves all verification jobs created in the last 24 hours,
    formats them into a CSV file, and uploads the file to an S3 bucket. The CSV
    includes detailed information about each job and its items.
    The S3 key follows the pattern: 'jobs_export/{YYYY}/{MM}/{DD}.csv'
    Args:
        event (dict): AWS Lambda event object (not used in this function)
        context (object): AWS Lambda context object (not used in this function)
    Returns:
        None: The function does not return any value but logs the results of the operation
    Dependencies:
        - asyncio: For handling async operations in a synchronous context
        - time: For timestamp calculations and formatting
        - BytesIO: For creating in-memory binary buffers
        - list_verification_jobs: Async function to fetch jobs from the database
        - upload_to_s3: Function to upload data to S3
    Notes:
        If no verification jobs are found for the specified time period, the function
        will log a message and exit without creating or uploading a CSV file.
    """
    print("Data exporter handler invoked")
    
    # Grab all the verification jobs from the database that have been created in the last 24 hours
    current_time = int(time.time())
    
    # Run the async function in a synchronous context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        jobs = loop.run_until_complete(list_verification_jobs(created_after=current_time - 86400))  # 86400 seconds = 24 hours
    finally:
        loop.close()
        
    if not jobs or len(jobs) == 0:
        print("No verification jobs found to export")
        return
    
    print(f"Found {len(jobs)} verification jobs to export")
    
    # Format of the S3 key is 'jobs_export/{YYMMDD}.csv}'
    export_csv_key = f"jobs_export/{time.strftime('%Y')}/{time.strftime('%m')}/{time.strftime('%d')}.csv"
    
    # Write the jobs to a CSV file and then upload it to S3
    # Use BytesIO to create a binary buffer for S3 upload
    with BytesIO() as buffer:
        # Build CSV content as string first
        csv_content = "job_id,created_at,updated_at,collection_id,collection_name,status,confidence,cost,total_cost,item_name,item_description,item_status,item_reason\n"
        
        # Write each job
        for job in jobs:
            for item in job.items:
                item_name = item.name if item.name else ""
                item_description = item.description if item.description else ""
                item_status=str(item.status) if item.status else ""
                item_reason = item.assessment_reasoning.replace('\n', '; ') if item.assessment_reasoning else ""
                job_id = job.id
                created_at = job.created_at
                updated_at = job.updated_at
                collection_id = job.collection_id
                worker_order_name = job.collection_name if job.collection_name else ""
                status = job.status.value if job.status else ""
                confidence = job.confidence if job.confidence is not None else ""
                cost = job.cost if job.cost is not None else ""
                total_cost = job.total_cost if job.total_cost is not None else ""
                
                # Add the row to CSV content
                csv_content += f"{job_id},{created_at},{updated_at},{collection_id},{worker_order_name},{status},{confidence},{cost},{total_cost},{item_name},{item_description},{item_status},{item_reason}\n"
            
        # Write the encoded content to the buffer
        buffer.write(csv_content.encode('utf-8'))
        
        # Move the file pointer to the beginning of the buffer
        buffer.seek(0)
        
        # Upload to S3
        upload_to_s3(buffer, export_csv_key)
        
        print("CSV file uploaded to S3 successfully to key:", export_csv_key)
        

# For local testing, you can call the handler function directly
if __name__ == "__main__":
    handler(None, None)
