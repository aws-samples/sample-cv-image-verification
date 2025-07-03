# Computer Vision Inspection System

This AI-powered computer vision inspection system that automates the verification of files against predefined criteria using Large Language Models (LLMs) and image analysis. This repository contains a monorepo for the complete application stack.

## Overview

This sample enables organizations to:
- Define **Items** with specific criteria (visual and description-based filtering rules)
- Upload **Collections** of files (primarily images) for inspection
- Run automated **Verification Jobs** that use AI to determine if files meet the defined criteria
- Track assessment results, confidence scores, and processing costs
- Manage LLM configurations and system prompts

## Project Structure

This is a monorepo managed with [pnpm](https://pnpm.io/) workspaces, containing the following packages:

- `packages/api`: FastAPI backend service for AWS Lambda providing the Ops Transformation API
- `packages/web`: React frontend web application with [AWS Cloudscape](https://cloudscape.design/) UI components
- `packages/api-ts-client`: TypeScript client library for the API
- `packages/infra`: AWS CDK infrastructure for deploying the complete system
- Refer to `THREAT_MODEL.md` for threat model

## Core Concepts

### Agents
An agent helps to provide extra information to item descriptions. For example, if you are creating an item for a car engine inspection verification, you could use an agent that can look up detailed engine specifications so that the LLM is able to perform detailed analysis. There are currently 3 types of agents supported:
- Amazon Bedrock Knowledge Base
- Amazon Athena
- REST Endpoint

### Items
Items define what you're looking for in your image collections. Each item contains:
- **Agents**: You can link items to one or more agents to augment the description filtering rules. For example, you might have an agent that can fetch data from a Bedrock Knowledge Base that contains technical specifications, business processes or other relevant information. The agent is used to lookup the relevant data. This is useful in not having to constantly repeat descriptions.
- **Label Filtering Rules**: Image-based criteria using computer vision (detect specific objects, minimum confidence scores)
- **Description Filtering Rules**: Text-based criteria for image descriptions
- **Cluster Requirements**: Logical grouping of rules for complex compliance scenarios

### Collections  
Collections are groups of files (typically images) that need to be verified against item criteria. They can include:
- Multiple file uploads with S3 storage
- Optional address information for location-based verification
- Associated metadata and descriptions

### Verification Jobs
Automated processes that evaluate collections against items using:
- AI/LLM analysis (Claude, etc.) for intelligent image assessment
- Ability to execute internet searches if required to look up more information if needed
- Confidence scoring and reasoning
- Cost tracking for AI processing
- Detailed logging and audit trails

## Architecture

The system uses a serverless AWS architecture:

### DynamoDB Tables
- **VerificationJobsTable**: Stores job information and status with GSIs for status-based queries and collection ID lookups
- **VerificationJobLogsTable**: Time-ordered logs and events with GSI for querying logs by verification job ID
- **ItemsTable**: Stores item definitions with filtering rules and criteria for verification
- **CollectionsTable**: Stores collections of files for verification with GSI for status-based queries
- **FileChecksTable**: File verification results for specific item instances within verification jobs
- **LlmConfigTable**: LLM configuration with version history and GSI for active configuration queries

### Key Features
- **Image Grid Processing**: Automatically creates image grids for efficient LLM analysis
- **Batch Processing**: Support for bulk verification jobs
- **Address Matching**: Location-based verification capabilities
- **Token Usage Tracking**: Monitor AI processing costs
- **Second-Pass Verification**: Optional re-verification for quality assurance

## Architecture

![Architecture Diagram](./docs/architecture.png)

### Components

### User Interface

**Component**: The end-user of the system.  
**Role**: To interact with the web application to submit collections and review analysis results. This is a user interface for demonstration of the prototype functionality, and uses a React.JS frontend using TypeScript and Vite.  
**Integrations**: Interacts with the Static Website Distribution via a web browser.

### WAF (Web Application Firewall)

**Component**: AWS WAF is a web application firewall that helps protect web applications from common web exploits.  
**Role**: To filter malicious traffic and protect the application from common web attacks.  
**Integrations**: Sits in front of the Static Website Distribution, inspecting incoming HTTP/S requests.  
**Explanation**: Provides an essential security layer for the web application, ensuring data integrity and availability.

### Static Website Distribution (Amazon CloudFront)

**Component**: Amazon CloudFront is a content delivery network (CDN) service.  
**Role**: To securely deliver the static content (HTML, CSS, JavaScript, images) of the web application to the user with low latency and high transfer speeds.  
**Integrations**: Serves content from the Static Website Bucket and is protected by WAF. User requests for the web application are routed through this component.  
**Explanation**: Improves application performance and scalability by caching content closer to users.

### Static Website Bucket (Amazon S3)

**Component**: Amazon S3 (Simple Storage Service) is an object storage service.  
**Role**: To store the static assets (HTML, CSS, JavaScript files, images) for the front-end web application.  
**Integrations**: Provides the source content for the Static Website Distribution.  
**Explanation**: Highly durable, scalable, and cost-effective storage for static website content.

### Cognito Auth (Amazon Cognito)

**Component**: Amazon Cognito is an AWS service for managing user identity and authentication.  
**Role**: To handle user sign-up, sign-in, and access control for the web application, ensuring that only authorized users can access the API.  
**Integrations**: Integrates with the API to authorize requests. The front-end application redirects users to Cognito for authentication using the Cognito built-in authentication user interface.  
**Explanation**: Provides a secure and scalable user directory, supports social identity providers, and is designed to allow integration with enterprise identity providers (e.g. Active Directory) post prototype.

### API (Lambda Proxy with FastAPI)

**Component**: The backend application programming interface. This is an Amazon API Gateway endpoint that proxies requests to an AWS Lambda function running a FastAPI application.  

**Role**: To receive requests from the authenticated user (e.g., to submit collections, upload images), validate them, and trigger the processing workflow. It also handles writing data to DynamoDB tables.  

**Integrations**: Receives requests from the user via the Static Website Distribution (after authentication via Cognito). It writes images to the Storage Bucket and enqueues jobs in the Job Processing Queue. It also interacts with DynamoDB tables. 

**Explanation**: API Gateway provides a scalable and secure entry point for API calls. AWS Lambda allows for serverless execution of the FastAPI application, which is a modern, fast framework for building APIs with Python. The API also provides the capability to integrate directly with functionality without using the user interface.

### Storage Bucket (Amazon S3)

**Component**: Amazon S3 (Simple Storage Service) is an object storage service.

**Role**: To store the images associated with the collections that are uploaded by the user via the API.  

**Integrations**: The API (Lambda Proxy) writes images to this bucket. The Analysis Lambda reads images from this bucket for processing. 

**Explanation**: S3 is highly durable, scalable, and cost-effective for storing large amounts of data like images. It also integrates seamlessly with other AWS services like Lambda.

### Job Processing Queue (Amazon SQS)

**Component**: Amazon SQS (Simple Queue Service) is a message queuing service.  

**Role**: To decouple the initial API request from the longer-running image analysis process. It holds messages representing jobs (e.g., a new collection to be analysed).  

**Integrations**: The API (Lambda Proxy) sends messages (jobs) to this queue. The Analysis Lambda is invoked by messages in this queue.  

**Explanation**: SQS provides a reliable and scalable way to manage asynchronous tasks, preventing the API from being blocked by long-running processes and improving the resilience of the system.

### Analysis Lambda (AWS Lambda)

**Component**: AWS Lambda is a serverless compute function.  

**Role**: To perform the core analysis of the images and collection data. This includes retrieving images from the Storage Bucket, interacting with Amazon Rekognition and Amazon Bedrock for analysis (object detection, image validation), and accessing configuration from SSM Parameter Store. It then writes the results to the Verification Jobs DynamoDB table.  

**Integrations**: Invoked by messages from the Job Processing Queue. Reads images from the Storage Bucket. Uses Amazon Bedrock and Amazon Rekognition for analysis. Reads configuration from SSM Parameter Store. Reads data and writes results to DynamoDB tables. 

**Explanation**: Lambda is suitable for event-driven, asynchronous processing. It scales automatically and is cost-effective since you only pay for compute time consumed. [Strands Agents](https://strandsagents.com/) is used for the agentic functionality used during analysis.

### DynamoDB Tables (Amazon DynamoDB)

**Component**: Amazon DynamoDB is a NoSQL key-value and document database.

**Role**: 
- **Agents**: Stores information about the agents and their configuration.
- **Items**: Stores the information on items to be verified.
- **Collections**: Stores details about the collections.
- **Verification Jobs**: Stores the status and results of the image verification and analysis processes.
- **Configuration**: Stores application configuration, prompts and verification rules.

**Integrations**: The API (Lambda Proxy) likely writes initial data to items and collections tables. The Analysis Lambda writes results to the Verification Jobs table and may read from any of these tables for context or rules.  

**Explanation**: DynamoDB is a fully managed, highly scalable, and low-latency NoSQL database, suitable for applications with high I/O needs and flexible data models, common in serverless applications.

### SSM Parameter Store (AWS Systems Manager Parameter Store)

**Component**: AWS Systems Manager Parameter Store is a service to store configuration data and secrets.  

**Role**: To store configuration parameters for the application. The only current parameter being used is to store the ARN of a role that the Bedrock runtime assumes.  

**Integrations**: The Analysis Lambda reads configuration data (prompts, etc.) from the Parameter Store.  

**Explanation**: Provides a secure and manageable way to store and version application configuration and secrets, separating them from the application code.

### Amazon Bedrock

**Component**: Amazon Bedrock is a fully managed service that offers a choice of high-performing foundation models (FMs) via a single API. 
 
**Role**: To provide access to foundation models natural language understanding of item requirements, image analysis, and generating textual reasoning/explanations for anomalies.  

**Integrations**: The Analysis Lambda calls the Bedrock API to leverage foundation models for its analysis tasks. Prompts for Bedrock are stored in a DynamoDB table to make them configurable through the web interface.  

**Explanation**: Simplifies access to powerful foundation models, allowing the prototype to leverage generative AI capabilities without needing to manage the underlying infrastructure or train models from scratch. Bedrock also allows for the usage of newer FMs as they get released without significant code changes.

### Amazon Rekognition

**Component**: Amazon Rekognition is an AWS service that makes it simple to add computer vision capabilities without managing infrastructure.  

**Role**: To perform object label detection to perform a fast and cheap way of eliminating collection images before Amazon Bedrock is used for more expensive, slower detailed analysis.  

**Integrations**: The Analysis Lambda sends images (or references to images in S3) to the Rekognition API for analysis.  

**Explanation**: Provides pre-trained and customizable computer vision capabilities, reducing the development effort for image analysis tasks. It is used to detect a configurable set of labels as the first step to eliminating non-relevant collection images.


## Prerequisites

- [Node.js](https://nodejs.org/) (v20 recommended)
- [pnpm](https://pnpm.io/) package manager
- [Python](https://www.python.org/) 3.12 or higher
- [Docker](https://www.docker.com/) (for API client generation and containerized builds)
- [AWS Account](https://aws.amazon.com/) and configured credentials
- [AWS CDK CLI](https://docs.aws.amazon.com/cdk/v2/guide/cli.html) (for infrastructure deployment)

## Setup

```bash
# Install all dependencies
pnpm install

# Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
cd packages/api
pip install -r requirements.txt
cd ../..
```

Note: This solution has the ability to integrate with [Tavily](https://www.tavily.com) to perform internet searches. The Tavily API key needs to be set in AWS Secrets Manager, which is setup via AWS CDK in `packages/infra/src/infra-stack.ts`. You need to create an account with Tavily and obtain an API key. Note that charges might be incurred for using the API.

## Building Packages

### Build Everything

```bash
# Build all packages
pnpm -r build
```

## Infrastructure Deployment

```bash
# Synthesize CloudFormation templates
pnpm synth

# Deploy to AWS
pnpm deploy

# Or deploy directly with CDK
cd packages/infra
npx cdk deploy

# Compare with deployed stack
npx cdk diff
```

Note that you will need to setup users in the Cognito User Pool after the stack has been newly deployed. Take a note of the Cognito User Pool ID in the CDK output, and use the AWS Management Console to add users.

## Running Locally (Post-Deployment)

### Setup Environment
1. Deploy the infrastructure to AWS first
2. Create a `.env` file in `packages/api/` using the `.env.template` with values from CDK output
3. Initialize LLM configuration (see LLM Configuration section below)

### Start Services

```bash
# Start API backend
cd packages/api
source ../../.venv/bin/activate
python api.py
```

```bash
# Start React frontend (in separate terminal)
cd packages/web
npm run dev
```

### API TypeScript Client Generation (Optional)

```bash
# Generate client from OpenAPI spec
# Note: API server must be running on localhost:8000
cd packages/api-ts-client
./generate-client.sh
```

## LLM Configuration System

This sample includes a LLM configuration system that manages:

### Configuration Types
1. **System Prompt** (`system_prompt`): Instructions for the LLM on how to analyze images
2. **Model ID** (`model_id`): The LLM model identifier (e.g., "anthropic.claude-3-5-sonnet-20241022-v2:0")
3. **Second Pass Verification**: Enable/disable second-pass processing for enhanced accuracy

### Configuration Management
- **Version History**: All configuration changes are tracked with timestamps
- **Active Status**: Only one configuration per type is active at a time
- **API Endpoints**: RESTful API for configuration management
- **Helper Functions**: Utilities in `utils/config_helpers.py` for easy access

### Initialization

```bash
# Initialize with default values
cd packages/api
python scripts/init_llm_config.py

# Force overwrite existing configuration
python scripts/init_llm_config.py --force

# Test current configuration
python scripts/test_llm_config.py
```

## Development Workflow

1. **Backend Development**: Start API server (`python api.py`)
2. **Frontend Development**: Run React dev server (`pnpm run dev`)
3. **Schema Changes**: Regenerate TypeScript client (`./generate-client.sh`)
4. **Infrastructure Changes**: Update and redeploy CDK stack
5. **Testing**: Use the web interface to create items, collections, and verification jobs

## User Interface

The React frontend provides:
- **Items Management**: Create and configure verification criteria
- **Collections Management**: Upload and organize files for inspection
- **Verification Jobs**: Monitor and review automated assessments
- **Configuration**: Manage LLM settings and system prompts

Navigation includes:
- Home dashboard
- Items listing and detail pages
- Collections management
- Verification jobs tracking
- System configuration

## API Endpoints

The FastAPI backend provides comprehensive REST endpoints:
- `/items/*` - Item management and filtering rules
- `/collections/*` - File collections and uploads
- `/verification-jobs/*` - Job creation, monitoring, and results
- `/llm-config/*` - LLM configuration management
- `/health` - System health checks

## License

MIT-0. See LICENSE file for details.

## Support

For issues or questions about this sample, please refer to the project documentation or contact the development team.

## ⚠️ AWS Cost Warning

**Important**: This application deploys AWS resources that will incur costs while running, including:
- DynamoDB tables with on-demand billing
- Lambda functions with compute charges
- S3 storage for file uploads
- Bedrock/Claude API calls for AI processing (can be significant with large volumes)
- API Gateway requests
- CloudWatch logs and monitoring

**Monitor your AWS costs regularly** and consider setting up billing alerts. AI/LLM processing costs can scale significantly with usage volume and model selection.

## Tearing Down Infrastructure

To avoid ongoing AWS costs, you can tear down the deployed infrastructure using the following commands:

### Complete Teardown (Recommended)

```bash
# Destroy all AWS resources
cd packages/infra
npx cdk destroy

# Or using pnpm from root directory
pnpm destroy
```

### Manual Cleanup (If CDK Destroy Fails)

If automated teardown encounters issues, you may need to manually clean up:

1. **Empty S3 Buckets**: 
   - Go to AWS S3 Console
   - Empty all buckets created by the stack (they cannot be deleted if not empty)
   - Delete the buckets

2. **Delete DynamoDB Tables**:
   - Go to AWS DynamoDB Console  
   - Delete tables: `VerificationJobsTable`, `VerificationJobLogsTable`, `ItemsTable`, `CollectionsTable`, `FileChecksTable`, `LlmConfigTable`

3. **Remove Lambda Functions**:
   - Go to AWS Lambda Console
   - Delete all functions created by the stack

4. **Clean up CloudWatch Logs**:
   - Go to AWS CloudWatch Console
   - Delete log groups associated with Lambda functions

5. **Remove API Gateway**:
   - Go to AWS API Gateway Console
   - Delete the API

6. **Delete CloudFormation Stack**:
   - Go to AWS CloudFormation Console
   - Delete the stack if it still exists

### Verify Cleanup

After teardown, verify all resources are removed by checking the AWS CloudFormation Console to ensure no related stacks remain, and review your AWS billing dashboard to confirm resources are no longer incurring charges.
