import { Construct } from "constructs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as ecr from "aws-cdk-lib/aws-ecr-assets";
import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as events from "aws-cdk-lib/aws-events"; // Add import for EventBridge
import * as targets from "aws-cdk-lib/aws-events-targets"; // Add import for EventBridge targets
import path = require("path");
import { Table } from "aws-cdk-lib/aws-dynamodb";
import { Stack } from "aws-cdk-lib";

export interface ExporterConstructProps {
  readonly verificationJobsTable: Table;
  readonly itemsTable: Table;
  readonly collectionsTable: Table;
  readonly fileChecksTable: Table;
  readonly llmConfigTable: Table;
  readonly verificationJobLogsTable: Table;
}

export class ExporterConstruct extends Construct {
  // Expose the Lambda function as a public property
  public readonly exporterFunction: lambda.DockerImageFunction;

  constructor(scope: Construct, id: string, props: ExporterConstructProps) {
    super(scope, id);

    const exporterStorageLogsBucket = new s3.Bucket(
      this,
      "ExporterStorageLogsBucket",
      {
        encryption: s3.BucketEncryption.S3_MANAGED,
        blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
        removalPolicy: cdk.RemovalPolicy.DESTROY,
        autoDeleteObjects: true,
        enforceSSL: true,
      }
    );

    const exportBucket = new s3.Bucket(this, "ExportBucket", {
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      serverAccessLogsBucket: exporterStorageLogsBucket,
      serverAccessLogsPrefix: "exportlogs",
    });

    // Build the Docker image from the API package
    const dockerImageAsset = new ecr.DockerImageAsset(
      this,
      "ExporterDockerImage",
      {
        directory: path.join(__dirname, "../../../api"),
        file: "exporter.Dockerfile",
        platform: cdk.aws_ecr_assets.Platform.LINUX_ARM64,
      }
    );

    // Create Lambda function from the Docker image
    this.exporterFunction = new lambda.DockerImageFunction(
      this,
      "ExporterFunction",
      {
        code: lambda.DockerImageCode.fromEcr(dockerImageAsset.repository, {
          tag: dockerImageAsset.imageTag,
        }),
        memorySize: 2048,
        timeout: cdk.Duration.seconds(30),
        environment: {
          EXPORT_BUCKET_NAME: exportBucket.bucketName,
          VERIFICATION_JOBS_TABLE_NAME: props.verificationJobsTable.tableName,
          ITEMS_TABLE_NAME: props.itemsTable.tableName,
          COLLECTIONS_TABLE_NAME: props.collectionsTable.tableName,
          FILE_CHECKS_TABLE_NAME: props.fileChecksTable.tableName,
          VERIFICATION_JOB_LOGS_TABLE_NAME:
            props.verificationJobLogsTable.tableName,
          STAGE: Stack.of(this).stackName || "dev",
        },
        architecture: lambda.Architecture.ARM_64,
      }
    );
    exportBucket.grantReadWrite(this.exporterFunction.role!);
    props.verificationJobsTable.grantReadWriteData(this.exporterFunction.role!);
    props.verificationJobLogsTable.grantReadWriteData(
      this.exporterFunction.role!
    );
    props.itemsTable.grantReadWriteData(this.exporterFunction.role!);
    props.collectionsTable.grantReadWriteData(this.exporterFunction.role!);
    props.fileChecksTable.grantReadWriteData(this.exporterFunction.role!);
    props.llmConfigTable.grantReadWriteData(this.exporterFunction.role!);

    // Add specific permissions instead of admin access
    const exporterPolicy = new cdk.aws_iam.PolicyStatement({
      actions: [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
      ],
      resources: [
        `arn:aws:logs:${cdk.Stack.of(this).region}:${
          cdk.Stack.of(this).account
        }:log-group:/aws/lambda/*`,
      ],
    });
    this.exporterFunction.role!.addToPrincipalPolicy(exporterPolicy);

    // Create an EventBridge rule to schedule the Lambda function
    // Schedule to run at 3AM AEST (UTC+10) every day
    // In cron expressions, UTC is used, so 3AM AEST is 17:00 UTC the previous day (17:00 UTC)
    const scheduleRule = new events.Rule(this, "DailyExportSchedule", {
      schedule: events.Schedule.cron({
        minute: "0",
        hour: "17",
        day: "*",
        month: "*",
        year: "*",
      }),
      description:
        "Triggers the exporter Lambda function every day at 3AM AEST",
    });

    // Add the Lambda function as a target for the rule
    scheduleRule.addTarget(new targets.LambdaFunction(this.exporterFunction));
  }
}
