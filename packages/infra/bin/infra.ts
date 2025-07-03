#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { InfraStack } from "../src/infra-stack";
import { AwsPrototypingChecks, PDKNag } from "@aws/pdk/pdk-nag";

const app = PDKNag.app({ nagPacks: [new AwsPrototypingChecks()] });
new InfraStack(app, "ImageVerificationDevStack", {
  /* Use the current AWS CLI configuration to determine account and region */
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },

  /* Add description to the CloudFormation stack */
  description:
    "Infrastructure for Computer Vision Verification Sample API with Lambda and API Gateway",

  /* Add tags for better resource management */
  tags: {
    Project: "Computer Vision Verification",
    Service: "API",
    Environment: process.env.ENVIRONMENT || "dev",
  },
});
