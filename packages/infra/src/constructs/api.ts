import * as path from "path";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigw from "aws-cdk-lib/aws-apigateway";
import * as iam from "aws-cdk-lib/aws-iam";
import * as ecr from "aws-cdk-lib/aws-ecr-assets";
import * as cdk from "aws-cdk-lib";
import { Bucket } from "aws-cdk-lib/aws-s3";
import { Table } from "aws-cdk-lib/aws-dynamodb";
import { StringParameter } from "aws-cdk-lib/aws-ssm";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as location from "aws-cdk-lib/aws-location";
import * as wafv2 from "aws-cdk-lib/aws-wafv2";
import { platform } from "os";
import { Secret } from "aws-cdk-lib/aws-secretsmanager";
export class ApiConstructProps {
  readonly verificationJobsTable: Table;
  readonly verificationJobLogsTable: Table;
  readonly storageBucket: Bucket;
  readonly itemsTable: Table;
  readonly fileChecksTable: Table;
  readonly collectionsTable: Table;
  readonly llmConfigTable: Table;
  readonly processingQueue: sqs.Queue;
  readonly placeIndex: location.CfnPlaceIndex;
  readonly bedrockRoleArn: StringParameter;
  readonly agentsTable: Table;
  readonly tavilyApiKeySecret: Secret;
}

export class ApiConstruct extends Construct {
  public readonly api: apigw.RestApi;
  public readonly webAcl: wafv2.CfnWebACL;

  constructor(scope: Construct, id: string, props: ApiConstructProps) {
    super(scope, id);

    const { storageBucket } = props;

    // Build the Docker image from the API package
    const dockerImageAsset = new ecr.DockerImageAsset(this, "ApiDockerImage", {
      directory: path.join(__dirname, "../../../api"),
      file: "api.Dockerfile",
      platform: cdk.aws_ecr_assets.Platform.LINUX_ARM64,
    });

    // Create Lambda function from the Docker image
    const apiFunction = new lambda.DockerImageFunction(this, "ApiFunction", {
      code: lambda.DockerImageCode.fromEcr(dockerImageAsset.repository, {
        tag: dockerImageAsset.imageTag,
      }),
      memorySize: 2048,
      timeout: cdk.Duration.seconds(30),
      environment: {
        STORAGE_BUCKET_NAME: storageBucket.bucketName,
        VERIFICATION_JOBS_TABLE_NAME: props.verificationJobsTable.tableName,
        ITEMS_TABLE_NAME: props.itemsTable.tableName,
        FILE_CHECKS_TABLE_NAME: props.fileChecksTable.tableName,
        COLLECTIONS_TABLE_NAME: props.collectionsTable.tableName,
        STAGE: "prod",
        LOCATION_INDEX_NAME: props.placeIndex.indexName,
        PROCESSING_QUEUE_URL: props.processingQueue.queueUrl,
        VERIFICATION_JOB_LOGS_TABLE_NAME:
          props.verificationJobLogsTable.tableName,
        LLM_CONFIG_TABLE_NAME: props.llmConfigTable.tableName,
        BEDROCK_ROLE_ARN_PARAMETER: props.bedrockRoleArn.parameterName,
        AGENTS_TABLE_NAME: props.agentsTable.tableName,
        TAVILY_API_KEY_SECRET: props.tavilyApiKeySecret.secretName,
      },
      architecture: lambda.Architecture.ARM_64,
    });

    storageBucket.grantReadWrite(apiFunction.role!);
    props.tavilyApiKeySecret.grantRead(apiFunction.role!);
    props.agentsTable.grantReadWriteData(apiFunction.role!);
    props.bedrockRoleArn.grantRead(apiFunction.role!);
    props.verificationJobsTable.grantReadWriteData(apiFunction.role!);
    props.itemsTable.grantReadWriteData(apiFunction.role!);
    props.fileChecksTable.grantReadWriteData(apiFunction.role!);
    props.collectionsTable.grantReadWriteData(apiFunction.role!);
    props.verificationJobLogsTable.grantReadWriteData(apiFunction.role!);
    props.llmConfigTable.grantReadWriteData(apiFunction.role!);

    // Add Rekognition permissions
    const rekognitionPolicy = new iam.PolicyStatement({
      actions: [
        "rekognition:DetectLabels",
        "rekognition:DetectModerationLabels",
      ],
      resources: ["*"], // Rekognition actions don't support resource-level permissions
    });
    apiFunction.role!.addToPrincipalPolicy(rekognitionPolicy);

    // Add Bedrock permissions
    const bedrockPolicy = new iam.PolicyStatement({
      actions: [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:GetFoundationModel",
        "bedrock:ListFoundationModels",
      ],
      resources: [
        `arn:aws:bedrock:${cdk.Stack.of(this).region}::foundation-model/*`,
        `arn:aws:bedrock:${cdk.Stack.of(this).region}:${
          cdk.Stack.of(this).account
        }:*`,
      ],
    });
    apiFunction.role!.addToPrincipalPolicy(bedrockPolicy);

    // Add Location services permissions
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
    apiFunction.role!.addToPrincipalPolicy(locationPolicy);

    // Add STS permissions for role assumption
    const stsPolicy = new iam.PolicyStatement({
      actions: ["sts:AssumeRole"],
      resources: [
        `arn:aws:iam::${cdk.Stack.of(this).account}:role/*bedrock*`,
        `arn:aws:iam::${cdk.Stack.of(this).account}:role/*Bedrock*`,
      ],
    });
    apiFunction.role!.addToPrincipalPolicy(stsPolicy);

    props.processingQueue.grantSendMessages(apiFunction.role!);

    // Create API Gateway with IAM authentication
    this.api = new apigw.RestApi(this, "ApiGateway", {
      restApiName: "Computer Vision Verification API",
      description: "API Gateway for Computer Vision Verification Sample",
      defaultCorsPreflightOptions: {
        allowOrigins: apigw.Cors.ALL_ORIGINS,
        allowMethods: apigw.Cors.ALL_METHODS,
        allowHeaders: [
          "Content-Type",
          "Authorization",
          "X-Amz-Date",
          "X-Api-Key",
          "X-Amz-Security-Token",
          "X-Amz-Content-Sha256",
        ],
        allowCredentials: true,
      },
    });

    // Configure IAM authentication
    const apiIntegration = new apigw.LambdaIntegration(apiFunction, {
      proxy: true,
    });

    // Add IAM authentication to API methods
    const rootResource = this.api.root;
    rootResource.addMethod("ANY", apiIntegration, {
      authorizationType: apigw.AuthorizationType.IAM,
    });

    // Add proxy resource to handle all routes
    const proxyResource = rootResource.addResource("{proxy+}");
    proxyResource.addMethod("ANY", apiIntegration, {
      authorizationType: apigw.AuthorizationType.IAM,
    });

    // Create WAF WebACL
    this.webAcl = new wafv2.CfnWebACL(this, "ApiWebACL", {
      scope: "REGIONAL",
      defaultAction: { allow: {} },
      rules: [
        {
          name: "AWSManagedRulesCommonRuleSet",
          priority: 1,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: "AWS",
              name: "AWSManagedRulesCommonRuleSet",
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: "CommonRuleSetMetric",
          },
        },
        {
          name: "AWSManagedRulesKnownBadInputsRuleSet",
          priority: 2,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: "AWS",
              name: "AWSManagedRulesKnownBadInputsRuleSet",
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: "KnownBadInputsRuleSetMetric",
          },
        },
        {
          name: "RateLimitRule",
          priority: 3,
          action: { block: {} },
          statement: {
            rateBasedStatement: {
              limit: 2000,
              aggregateKeyType: "IP",
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: "RateLimitRuleMetric",
          },
        },
      ],
      visibilityConfig: {
        sampledRequestsEnabled: true,
        cloudWatchMetricsEnabled: true,
        metricName: "ApiWebACLMetric",
      },
    });

    // Associate WebACL with API Gateway
    new wafv2.CfnWebACLAssociation(this, "ApiWebACLAssociation", {
      resourceArn: `arn:aws:apigateway:${
        cdk.Stack.of(this).region
      }::/restapis/${this.api.restApiId}/stages/${
        this.api.deploymentStage.stageName
      }`,
      webAclArn: this.webAcl.attrArn,
    });

    // Output the API URL
    new cdk.CfnOutput(this, "ApiUrl", {
      value: this.api.url,
      description: "Endpoint URL of the API",
    });

    // Output the WebACL ARN
    new cdk.CfnOutput(this, "WebAclArn", {
      value: this.webAcl.attrArn,
      description: "ARN of the WAF WebACL protecting the API",
    });
  }
}
