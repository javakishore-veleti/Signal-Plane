import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as apigw from 'aws-cdk-lib/aws-apigatewayv2';
import * as integrations from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import { Construct } from 'constructs';

export interface IngestStackProps extends cdk.StackProps {
  stage: string;
  payloadBucket: s3.Bucket;
  signalTable: dynamodb.Table;
}

/**
 * One Lambda per source (ADR-0003), plus the outbound ingest endpoint the edge
 * shipper posts to (ADR-0007). Adapters are added here without touching anything
 * that already exists, which is the property the whole design is buying.
 */
export class IngestStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: IngestStackProps) {
    super(scope, id, props);

    const dlq = new sqs.Queue(this, 'IngestDlq', { retentionPeriod: cdk.Duration.days(14) });

    const adapter = (name: string, path: string) => {
      const fn = new lambda.Function(this, `Adapter${name}`, {
        runtime: lambda.Runtime.PYTHON_3_12,
        handler: `${path}.handler`,
        code: lambda.Code.fromAsset('../../adapters/python'),
        timeout: cdk.Duration.minutes(5),
        memorySize: 512,
        deadLetterQueue: dlq,
        environment: {
          OBJECT_BUCKET: props.payloadBucket.bucketName,
          SIGNAL_TABLE: props.signalTable.tableName,
        },
      });
      props.payloadBucket.grantPut(fn);
      props.signalTable.grantWriteData(fn);
      return fn;
    };

    adapter('DirectoryWatch', 'sources/directory_watch/handler');

    // Estate ingest. Bearer authorised, outbound initiated by the customer estate,
    // no inbound path into the customer network in either direction.
    const estateIngest = adapter('EstateIngest', 'sources/estate_ingest/handler');
    const api = new apigw.HttpApi(this, 'IngestApi', { description: 'Edge shipper ingest' });
    api.addRoutes({
      path: '/v1/ingest/batch',
      methods: [apigw.HttpMethod.POST],
      integration: new integrations.HttpLambdaIntegration('EstateIngestInt', estateIngest),
    });

    new cdk.CfnOutput(this, 'IngestEndpoint', { value: api.apiEndpoint });
    new cdk.CfnOutput(this, 'DlqUrl', { value: dlq.queueUrl });
  }
}
