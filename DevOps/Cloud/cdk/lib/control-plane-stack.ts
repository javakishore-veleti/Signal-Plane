import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecsPatterns from 'aws-cdk-lib/aws-ecs-patterns';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export interface ControlPlaneStackProps extends cdk.StackProps {
  stage: string;
  vpc: ec2.Vpc;
  policyTable: dynamodb.Table;
}

/**
 * The control plane runs as a long lived container rather than a function: it holds
 * connection pools and policy caches, and its traffic is steady and low volume.
 * That is the opposite profile to the adapters, which is exactly why the two are
 * deployed differently (ADR-0005).
 */
export class ControlPlaneStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: ControlPlaneStackProps) {
    super(scope, id, props);

    const cluster = new ecs.Cluster(this, 'Cluster', {
      vpc: props.vpc,
      containerInsights: props.stage === 'prod',
    });

    const service = new ecsPatterns.ApplicationLoadBalancedFargateService(this, 'ControlPlane', {
      cluster,
      cpu: 512,
      memoryLimitMiB: 1024,
      desiredCount: props.stage === 'prod' ? 2 : 1,
      publicLoadBalancer: false,
      taskImageOptions: {
        image: ecs.ContainerImage.fromAsset('../../services/control-plane'),
        containerPort: 8080,
        environment: { POLICY_TABLE: props.policyTable.tableName, STAGE: props.stage },
      },
    });

    service.targetGroup.configureHealthcheck({ path: '/actuator/health', healthyThresholdCount: 2 });
    props.policyTable.grantReadWriteData(service.taskDefinition.taskRole);

    service.service.autoScaleTaskCount({ minCapacity: 1, maxCapacity: 4 })
      .scaleOnCpuUtilization('CpuScaling', { targetUtilizationPercent: 65 });

    new cdk.CfnOutput(this, 'ControlPlaneUrl', {
      value: `http://${service.loadBalancer.loadBalancerDnsName}`,
    });
  }
}
