# Ops Transformation API

FastAPI backend designed to run on AWS Lambda using Mangum adapter.

## Development Setup

### Prerequisites

- Python 3.12
- pip or pipenv
- Docker (for local container testing)
- AWS CLI (for deployment)

### Local Development

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   cd   # On Windows use: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   python3 api.py
   ```

4. Access the API at http://localhost:8000
   - API documentation is available at http://localhost:8000/docs

## Docker

### Building the Docker Image

```bash
docker build -t pace-api .
```

### Running the Container Locally

```bash
docker run -p 9000:8080 pace-api
```

This will expose the Lambda function at: http://localhost:9000/2015-03-31/functions/function/invocations

## AWS Lambda Deployment

### Manual Deployment

1. Build the Docker image:
   ```bash
   docker build -t pace-api .
   ```

2. Tag the image for ECR:
   ```bash
   docker tag pace-api:latest [AWS_ACCOUNT_ID].dkr.ecr.[REGION].amazonaws.com/pace-api:latest
   ```

3. Push to ECR:
   ```bash
   aws ecr get-login-password --region [REGION] | docker login --username AWS --password-stdin [AWS_ACCOUNT_ID].dkr.ecr.[REGION].amazonaws.com
   docker push [AWS_ACCOUNT_ID].dkr.ecr.[REGION].amazonaws.com/pace-api:latest
   ```

4. Create or update the Lambda function to use the container image.

## Components

### Main API (api.py)
FastAPI backend designed to run on AWS Lambda using Mangum adapter. Provides REST API endpoints for managing verification jobs, collections, items, and agents.

### Data Exporter (exporter.py)
AWS Lambda function that exports verification job data to S3 in CSV format. This component:

- Runs as a scheduled Lambda function (typically daily)
- Retrieves verification jobs created in the last 24 hours
- Exports job data including items, status, confidence scores, and costs to CSV
- Uploads the CSV file to S3 with organized date-based folder structure (`jobs_export/YYYY/MM/DD.csv`)
- Handles AWS credentials and S3 upload errors gracefully

The exporter is containerized using `exporter.Dockerfile` and deployed as a separate Lambda function.

### Queue Batch Work Orders (queue_batch_workorders.py)
Processes batch work orders from a queue system.

### Verification Job Processor (verification_job_processor.py)
Handles the processing of verification jobs asynchronously.

## Project Structure

```
packages/api/
├── api.py                # Main FastAPI application
├── exporter.py           # Data export Lambda function
├── queue_batch_workorders.py  # Batch work order processor
├── verification_job_processor.py  # Job processor
├── constants.py          # Application constants
├── item_processing/      # Item processing modules
├── llm/                  # LLM integration modules
├── routers/              # API route handlers
├── schemas/              # Pydantic models for request/response
├── scripts/              # Utility scripts
├── tests/                # Test directory
├── utils/                # Utility modules
├── Dockerfile            # Main API container
├── exporter.Dockerfile   # Data exporter container
├── queue_batch_workorders.Dockerfile  # Batch processor container
├── verification_job_processor.Dockerfile  # Job processor container
├── README.md
└── requirements.txt      # Python dependencies
