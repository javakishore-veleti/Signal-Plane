import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export interface CoreStackProps extends cdk.StackProps { stage: string }

/** Substrate shared by everything else: network, object store, tables. */
export class CoreStack extends cdk.Stack {
  readonly vpc: ec2.Vpc;
  readonly payloadBucket: s3.Bucket;
  readonly signalTable: dynamodb.Table;
  readonly policyTable: dynamodb.Table;

  constructor(scope: Construct, id: string, props: CoreStackProps) {
    super(scope, id, props);

    // One NAT gateway, not one per AZ. NAT is usually the largest line item in a
    // dev account and the availability benefit is not worth it below production.
    this.vpc = new ec2.Vpc(this, 'Vpc', { maxAzs: 2, natGateways: 1 });

    this.payloadBucket = new s3.Bucket(this, 'PayloadBucket', {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      versioned: true,
      // Object lock is what makes legal hold enforceable at the store rather than
      // at the application, where it is one bad code path away from being bypassed.
      objectLockEnabled: true,
      lifecycleRules: [
        { id: 'standard-retention', expiration: cdk.Duration.days(365) },
        { id: 'abort-incomplete', abortIncompleteMultipartUploadAfter: cdk.Duration.days(7) },
      ],
      removalPolicy: props.stage === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: props.stage !== 'prod',
    });

    // Partition by (tenant, subject) so every read is naturally tenant scoped.
    // Cross tenant reads become impossible to express rather than merely forbidden.
    this.signalTable = new dynamodb.Table(this, 'SignalIndex', {
      partitionKey: { name: 'pk', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'sk', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: 'expires_at_epoch',
      pointInTimeRecovery: true,
      removalPolicy: props.stage === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    this.policyTable = new dynamodb.Table(this, 'PolicyStore', {
      partitionKey: { name: 'pk', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'sk', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: props.stage === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    new cdk.CfnOutput(this, 'PayloadBucketName', { value: this.payloadBucket.bucketName });
    new cdk.CfnOutput(this, 'SignalTableName', { value: this.signalTable.tableName });
  }
}
