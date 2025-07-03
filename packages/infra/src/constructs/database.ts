import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { CfnOutput, RemovalPolicy } from "aws-cdk-lib";

export class DatabaseConstruct extends Construct {
  public readonly verificationJobsTable: dynamodb.Table;
  public readonly verificationJobLogsTable: dynamodb.Table;
  public readonly itemsTable: dynamodb.Table;
  public readonly collectionsTable: dynamodb.Table;
  public readonly fileChecksTable: dynamodb.Table;
  public readonly llmConfigTable: dynamodb.Table;
  public readonly agentsTable: dynamodb.Table;

  constructor(scope: Construct, id: string) {
    super(scope, id);

    this.agentsTable = new dynamodb.Table(this, "AgentsTable", {
      partitionKey: {
        name: "id",
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY, // Use RETAIN in production
    });

    // --- Verification Jobs Table ---
    this.verificationJobsTable = new dynamodb.Table(
      this,
      "VerificationJobsTable",
      {
        partitionKey: {
          name: "id",
          type: dynamodb.AttributeType.STRING,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: RemovalPolicy.DESTROY, // Use RETAIN in production
        // pointInTimeRecovery: true,
      }
    );

    // GSI for querying Verification Jobs by status
    this.verificationJobsTable.addGlobalSecondaryIndex({
      indexName: "status-index",
      partitionKey: { name: "status", type: dynamodb.AttributeType.STRING },
      // Add sort key if needed for further filtering/sorting within a status
      // sortKey: { name: "createdAt", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    this.verificationJobsTable.addGlobalSecondaryIndex({
      indexName: "CollectionIdIndex", // Match the name used in the Python code
      partitionKey: {
        name: "collection_id",
        type: dynamodb.AttributeType.STRING,
      },
      // sortKey: { name: "createdAt", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL, // Project all attributes for simplicity
    });

    new CfnOutput(this, "VerificationJobsTableName", {
      value: this.verificationJobsTable.tableName,
    });

    // --- Verification Job Logs Table ---
    this.verificationJobLogsTable = new dynamodb.Table(
      this,
      "VerificationJobLogsTable",
      {
        partitionKey: {
          name: "id", // Primary key
          type: dynamodb.AttributeType.STRING,
        },
        sortKey: {
          name: "timestamp", // Sort key for time-based sorting
          type: dynamodb.AttributeType.NUMBER,
        },
        billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
        removalPolicy: RemovalPolicy.DESTROY, // Use RETAIN in production
        // pointInTimeRecovery: true,
      }
    );

    // GSI for querying logs by verification_job_id
    this.verificationJobLogsTable.addGlobalSecondaryIndex({
      indexName: "verification-job-id-index",
      partitionKey: {
        name: "verification_job_id",
        type: dynamodb.AttributeType.STRING,
      },
      // Explicitly define timestamp as the sort key for the GSI
      sortKey: { name: "timestamp", type: dynamodb.AttributeType.NUMBER },
      projectionType: dynamodb.ProjectionType.ALL, // Project all attributes
    });

    new CfnOutput(this, "VerificationJobLogsTableName", {
      value: this.verificationJobLogsTable.tableName,
    });

    this.itemsTable = new dynamodb.Table(this, "ItemsTable", {
      partitionKey: { name: "id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY, // Use RETAIN in production
      // pointInTimeRecovery: true,
    });

    new CfnOutput(this, "ItemsTableName", {
      value: this.itemsTable.tableName,
    });

    this.collectionsTable = new dynamodb.Table(this, "CollectionsTable", {
      partitionKey: {
        name: "id",
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY, // Use RETAIN in production
      // pointInTimeRecovery: true,
    });

    this.collectionsTable.addGlobalSecondaryIndex({
      indexName: "status-index",
      partitionKey: { name: "status", type: dynamodb.AttributeType.STRING },
      // sortKey: { name: "createdAt", type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    this.fileChecksTable = new dynamodb.Table(this, "fileChecksTable", {
      partitionKey: {
        name: "verification_job_id",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: "item_instance_id",
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY, // Use RETAIN in production
    });

    new CfnOutput(this, "FileChecksTableName", {
      value: this.fileChecksTable.tableName,
    });

    // --- LLM Config Table ---
    this.llmConfigTable = new dynamodb.Table(this, "LlmConfigTable", {
      partitionKey: {
        name: "config_type",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: "timestamp",
        type: dynamodb.AttributeType.NUMBER,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY, // Use RETAIN in production
    });

    // Add a GSI for querying active configurations
    this.llmConfigTable.addGlobalSecondaryIndex({
      indexName: "active-config-index",
      partitionKey: {
        name: "config_type",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: "is_active",
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    new CfnOutput(this, "LlmConfigTableName", {
      value: this.llmConfigTable.tableName,
    });
  }
}
