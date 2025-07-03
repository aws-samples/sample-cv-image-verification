import { Bucket } from "aws-cdk-lib/aws-s3";
import { Construct } from "constructs";
import * as s3 from "aws-cdk-lib/aws-s3";
import { CfnOutput, Duration, RemovalPolicy } from "aws-cdk-lib";

export class StorageConstruct extends Construct {
  public readonly storageBucket: s3.Bucket;
  public readonly storageLogsBucket: s3.Bucket;
  public readonly exportBucket: s3.Bucket;

  constructor(scope: Construct, id: string) {
    super(scope, id);
    this.storageLogsBucket = new Bucket(this, "StorageLogsBucket", {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      enforceSSL: true,
    });
    this.storageBucket = new Bucket(this, "StorageBucket", {
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: RemovalPolicy.RETAIN_ON_UPDATE_OR_DELETE,
      serverAccessLogsBucket: this.storageLogsBucket,
      serverAccessLogsPrefix: "logs",
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.PUT,
            s3.HttpMethods.POST,
            s3.HttpMethods.GET,
            s3.HttpMethods.HEAD,
          ], // Added GET/HEAD/POST for flexibility
          allowedOrigins: ["*", "http://localhost:3000"],
          allowedHeaders: ["*"],
          exposedHeaders: ["ETag"], // Expose ETag header
        },
      ],
      lifecycleRules: [
        {
          id: "TempUploadsExpiration",
          prefix: "temp-uploads/",
          expiration: Duration.days(1),
          enabled: true,
        },
      ],
    });

    new CfnOutput(this, "StorageBucketName", {
      value: this.storageBucket.bucketName,
    });
  }
}
