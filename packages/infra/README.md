# Infrastructure with AWS CDK

This package contains the AWS Cloud Development Kit (CDK) infrastructure code for the Computer Vision Inspection System.

## Infrastructure Components

- **Docker-based Lambda Function**: Deploys the FastAPI backend (`packages/api`) as a containerized Lambda function
- **API Gateway**: Exposes the Lambda function as a RESTful API with IAM authentication
- **IAM Roles and Policies**: Configures proper permissions for the infrastructure components

## Detailed Documentation

For detailed information about the API Lambda infrastructure, including deployment, authentication, and troubleshooting, see the [API Lambda Infrastructure Documentation](./README-API-LAMBDA.md).

## Prerequisites

- AWS CLI configured with appropriate credentials
- Docker installed and running (required for building container images)
- Node.js and npm installed
- pnpm for workspace package management

## Package Dependencies

This infrastructure package depends on the following workspace packages:

- `@aws-samples/cv-verification-api`: The FastAPI backend deployed as Lambda
- `@aws-samples/cv-verification-api-client`: TypeScript client for the API
- `@aws-samples/cv-verification-api-web`: React frontend web application

## Deployment

```bash
# Build the TypeScript code
npm run build

# Deploy the stack to AWS
npm run cdk deploy
# or
npx cdk deploy
```

## Useful Commands

* `npm run build`   Compile TypeScript to JavaScript
* `npm run watch`   Watch for changes and compile
* `npm run test`    Perform the Jest unit tests
* `npx cdk deploy`  Deploy this stack to your default AWS account/region
* `npx cdk diff`    Compare deployed stack with current state
* `npx cdk synth`   Emit the synthesized CloudFormation template

# TODO

Remove the STS assume role stuff from the LLM.py
