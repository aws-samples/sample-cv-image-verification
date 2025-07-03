import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import { ApiConstruct } from "./constructs/api";
import { UserIdentity } from "@aws/pdk/identity";
import { Effect, PolicyStatement } from "aws-cdk-lib/aws-iam";
import { CfnOutput, Stack, Names } from "aws-cdk-lib";
import { StaticWebsite } from "@aws/pdk/static-website";
import { StringParameter } from "aws-cdk-lib/aws-ssm";
import { ExporterConstruct } from "./constructs/exporter";
import {
  Mfa,
  StandardThreatProtectionMode,
  UserPool,
} from "aws-cdk-lib/aws-cognito";
import { StorageConstruct } from "./constructs/storage";
import { DatabaseConstruct } from "./constructs/database";
import { ProcessingWorkflowConstruct } from "./constructs/processing-workflow";
import { LocationConstruct } from "./constructs/location";
import * as path from "path";
import { rebuildTargetDir } from "./utils/rebuild";
import { GeoRestriction } from "aws-cdk-lib/aws-cloudfront";
import { Secret } from "aws-cdk-lib/aws-secretsmanager";

export class InfraStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const uid = Names.uniqueId(this);
    const location = new LocationConstruct(this, "LocationConstruct");

    const userPool = new UserPool(this, "UserPool", {
      selfSignUpEnabled: false,
      signInAliases: {
        email: true,
      },
      standardAttributes: {
        email: {
          required: true,
          mutable: false,
        },
      },
      mfa: Mfa.OPTIONAL,
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true,
      },
    });

    const userIdentity = new UserIdentity(this, "UserIdentity", {
      allowSignup: false,
      userPool: userPool,
      identityPoolOptions: {
        allowUnauthenticatedIdentities: false,
      },
    });

    const bedrockRoleArn = new StringParameter(
      this,
      "BedrockRoleArnParameter",
      {
        stringValue: "NA",
        parameterName: `/cv-verification/${uid}/bedrock-role-arn`,
      }
    );

    const storage = new StorageConstruct(this, "StorageConstruct");

    const data = new DatabaseConstruct(this, "DatabaseConstruct");

    const tavilyApiKeySecret = new Secret(this, "TavilyApiKeySecret", {
      description: "Tavily API key for web scraping",
    });

    const workflow = new ProcessingWorkflowConstruct(
      this,
      "ProcessingWorkflowConstruct",
      {
        agentsTable: data.agentsTable,
        placeIndex: location.placeIndex,
        verificationJobLogsTable: data.verificationJobLogsTable,
        storageBucket: storage.storageBucket,
        verificationJobsTable: data.verificationJobsTable,
        itemsTable: data.itemsTable,
        fileChecksTable: data.fileChecksTable,
        collectionsTable: data.collectionsTable,
        llmConfigTable: data.llmConfigTable,
        bedrockRoleArn,
        tavilyApiKeySecret,
      }
    );

    const api = new ApiConstruct(this, "ApiConstruct", {
      placeIndex: location.placeIndex,
      verificationJobLogsTable: data.verificationJobLogsTable,
      storageBucket: storage.storageBucket,
      verificationJobsTable: data.verificationJobsTable,
      itemsTable: data.itemsTable,
      fileChecksTable: data.fileChecksTable,
      collectionsTable: data.collectionsTable,
      llmConfigTable: data.llmConfigTable,
      processingQueue: workflow.processingQueue,
      agentsTable: data.agentsTable,
      bedrockRoleArn,
      tavilyApiKeySecret,
    });

    // Create the exporter construct with scheduled execution
    new ExporterConstruct(this, "ExporterConstruct", {
      verificationJobLogsTable: data.verificationJobLogsTable,
      verificationJobsTable: data.verificationJobsTable,
      itemsTable: data.itemsTable,
      collectionsTable: data.collectionsTable,
      fileChecksTable: data.fileChecksTable,
      llmConfigTable: data.llmConfigTable,
    });

    // Grant authenticated user permissions to call all control plane apis
    userIdentity.identityPool.authenticatedRole.addToPrincipalPolicy(
      new PolicyStatement({
        effect: Effect.ALLOW,
        actions: ["execute-api:Invoke"],
        resources: [api.api.arnForExecuteApi("*", "/*", "*")],
      })
    );

    // Rebuilds if target dir has changed since the last build.
    rebuildTargetDir(
      path.resolve(__dirname, "../../web/src"),
      path.resolve(__dirname, "../../web/dist"),
      "pnpm --filter @aws-samples/cv-verification-web build"
    );

    const web = new StaticWebsite(this, "CVImageVerificationStaticWebsite", {
      websiteContentPath: "../web/dist",
      runtimeOptions: {
        jsonPayload: {
          region: Stack.of(this).region,
          identityPoolId: userIdentity.identityPool.identityPoolId,
          userPoolId: userIdentity.userPool?.userPoolId,
          userPoolWebClientId: userIdentity.userPoolClient?.userPoolClientId,
          apiUrl: api.api.urlForPath(),
        },
      },
      distributionProps: {
        geoRestriction: GeoRestriction.allowlist("AU"),
        errorResponses: [
          {
            httpStatus: 404,
            responsePagePath: "/index.html",
            ttl: cdk.Duration.minutes(30),
          },
          {
            httpStatus: 403,
            responsePagePath: "/index.html",
            ttl: cdk.Duration.minutes(30),
          },
        ],
      },
    });

    new CfnOutput(this, "CVImageVerificationStaticWebsiteUrl", {
      value: `https://${web.cloudFrontDistribution.domainName}`,
    });
  }
}
