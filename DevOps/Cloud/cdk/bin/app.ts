#!/usr/bin/env node
/**
 * Stacks are deliberately small and separable so any one of them can be destroyed
 * without taking the rest with it (ADR-0010). Cost control is a design constraint
 * here, not an afterthought: the default posture is nothing running.
 */
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { CoreStack } from '../lib/core-stack';
import { IngestStack } from '../lib/ingest-stack';
import { ControlPlaneStack } from '../lib/control-plane-stack';

const app = new cdk.App();
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION ?? 'us-east-1',
};
const stage = app.node.tryGetContext('stage') ?? 'dev';

const core = new CoreStack(app, `SignalPlane-Core-${stage}`, { env, stage });

new IngestStack(app, `SignalPlane-Ingest-${stage}`, {
  env,
  stage,
  payloadBucket: core.payloadBucket,
  signalTable: core.signalTable,
});

new ControlPlaneStack(app, `SignalPlane-ControlPlane-${stage}`, {
  env,
  stage,
  vpc: core.vpc,
  policyTable: core.policyTable,
});

cdk.Tags.of(app).add('project', 'signal-plane');
cdk.Tags.of(app).add('stage', stage);
