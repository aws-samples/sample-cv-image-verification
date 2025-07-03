import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import { Bucket } from "aws-cdk-lib/aws-s3";
import * as path from "path";
import { Table } from "aws-cdk-lib/aws-dynamodb";
import * as location from "aws-cdk-lib/aws-location";
import { StringParameter } from "aws-cdk-lib/aws-ssm";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import { Secret } from "aws-cdk-lib/aws-secretsmanager";

export interface ProcessingWorkflowProps {
  readonly storageBucket: Bucket;
  readonly verificationJobsTable: Table;
  readonly verificationJobLogsTable: Table;
  readonly itemsTable: Table;
  readonly fileChecksTable: Table;
  readonly collectionsTable: Table;
  readonly llmConfigTable: Table;
  readonly placeIndex: location.CfnPlaceIndex;
  readonly bedrockRoleArn: StringParameter;
  readonly agentsTable: Table;
  readonly tavilyApiKeySecret: Secret;
}

export class ProcessingWorkflowConstruct extends Construct {
  public readonly processingQueue: sqs.Queue;

  constructor(scope: Construct, id: string, props: ProcessingWorkflowProps) {
    super(scope, id);

    const { storageBucket } = props;

    const lambdaEnvironmentVariables = {
      STORAGE_BUCKET_NAME: storageBucket.bucketName,
      VERIFICATION_JOBS_TABLE_NAME: props.verificationJobsTable.tableName,
      ITEMS_TABLE_NAME: props.itemsTable.tableName,
      FILE_CHECKS_TABLE_NAME: props.fileChecksTable.tableName,
      COLLECTIONS_TABLE_NAME: props.collectionsTable.tableName,
      LOCATION_INDEX_NAME: props.placeIndex.indexName,
      STAGE: "prod",
      VERIFICATION_JOB_LOGS_TABLE_NAME:
        props.verificationJobLogsTable.tableName,
      PLACE_INDEX_NAME: props.placeIndex.indexName,
      LLM_CONFIG_TABLE_NAME: props.llmConfigTable.tableName,
      BEDROCK_ROLE_ARN_PARAMETER: props.bedrockRoleArn.parameterName,
      AGENTS_TABLE_NAME: props.agentsTable.tableName,
      TAVILY_API_KEY_SECRET: props.tavilyApiKeySecret.secretName,
    };

    // Define Rekognition permissions
    const rekognitionPolicy = new iam.PolicyStatement({
      actions: [
        "rekognition:DetectLabels",
        "rekognition:DetectModerationLabels",
      ],
      resources: ["*"], // Rekognition actions don't support resource-level permissions
    });

    // Define Bedrock permissions
    const bedrockPolicy = new iam.PolicyStatement({
      actions: ["bedrock:*"],
      resources: [`*`],
    });

    // Define Location services permissions
    const locationPolicy = new iam.PolicyStatement({
      actions: [
        "geo:SearchPlaceIndexForText",
        "geo:SearchPlaceIndexForPosition",
        "geo:GetPlace",
      ],
      resources: [
        `arn:aws:geo:${cdk.Stack.of(this).region}:${
          cdk.Stack.of(this).account
        }:place-index/${props.placeIndex.indexName}`,
      ],
    });

    // Define STS permissions for role assumption
    const stsPolicy = new iam.PolicyStatement({
      actions: ["sts:AssumeRole"],
      resources: [
        `arn:aws:iam::${cdk.Stack.of(this).account}:role/*bedrock*`,
        `arn:aws:iam::${cdk.Stack.of(this).account}:role/*Bedrock*`,
      ],
    });

    // Define Lambda Functions from Dockerfiles
    const verificationProcessingJob = new lambda.DockerImageFunction(
      this,
      "VerificationJobFunction",
      {
        code: lambda.DockerImageCode.fromImageAsset(
          path.join(__dirname, "../../../api"),
          {
            file: "verification_job_processor.Dockerfile",
            platform: cdk.aws_ecr_assets.Platform.LINUX_ARM64,
          }
        ),
        memorySize: 10240,
        timeout: cdk.Duration.minutes(15),
        environment: lambdaEnvironmentVariables,
        architecture: lambda.Architecture.ARM_64,
      }
    );

    // Create an SQS queue to trigger the verification_job_processor function
    this.processingQueue = new sqs.Queue(this, "ProcessingQueue", {
      visibilityTimeout: cdk.Duration.minutes(15), // Match with Lambda timeout
      retentionPeriod: cdk.Duration.days(14),
      enforceSSL: true,
      deadLetterQueue: {
        queue: new sqs.Queue(this, "ProcessingDLQ", {
          retentionPeriod: cdk.Duration.days(14),
          enforceSSL: true,
        }),
        maxReceiveCount: 3,
      },
    });

    // Configure the verification_job_processor function to be triggered by the SQS queue
    verificationProcessingJob.addEventSource(
      new lambdaEventSources.SqsEventSource(this.processingQueue, {
        batchSize: 1, // Process one message at a time
        maxBatchingWindow: cdk.Duration.seconds(10),
        maxConcurrency: 5,
      })
    );

    // Define Lambda Functions from Dockerfiles
    const queueFunction = new lambda.DockerImageFunction(
      this,
      "QueueFunction",
      {
        code: lambda.DockerImageCode.fromImageAsset(
          path.join(__dirname, "../../../api"),
          {
            file: "queue_batch_workorders.Dockerfile",
            platform: cdk.aws_ecr_assets.Platform.LINUX_ARM64,
          }
        ),
        memorySize: 1024,
        timeout: cdk.Duration.minutes(15),
        environment: {
          ...lambdaEnvironmentVariables,
          PROCESSING_QUEUE_URL: this.processingQueue.queueUrl,
        },
        architecture: lambda.Architecture.ARM_64,
      }
    );

    const lambdas = [verificationProcessingJob, queueFunction];
    // Add permissions to the Lambda functions
    lambdas.forEach((lambdaFunction) => {
      storageBucket.grantReadWrite(lambdaFunction);
      props.tavilyApiKeySecret.grantRead(lambdaFunction);
      props.verificationJobsTable.grantReadWriteData(lambdaFunction);
      props.verificationJobLogsTable.grantReadWriteData(lambdaFunction);
      props.itemsTable.grantReadWriteData(lambdaFunction);
      props.fileChecksTable.grantReadWriteData(lambdaFunction);
      props.collectionsTable.grantReadWriteData(lambdaFunction);
      props.llmConfigTable.grantReadWriteData(lambdaFunction);
      props.agentsTable.grantReadWriteData(lambdaFunction);
      props.bedrockRoleArn.grantRead(lambdaFunction);
      lambdaFunction.role?.addToPrincipalPolicy(rekognitionPolicy);
      lambdaFunction.role?.addToPrincipalPolicy(bedrockPolicy);
      lambdaFunction.role?.addToPrincipalPolicy(locationPolicy);
      lambdaFunction.role?.addToPrincipalPolicy(stsPolicy);
    });

    // Grant send message permissions to the queue function
    this.processingQueue.grantSendMessages(queueFunction);
  }
}
