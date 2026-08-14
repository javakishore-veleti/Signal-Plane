# Deployment

## Posture

Nothing runs by default. Cloud resources cost money whether or not anyone is using them, so deployment is manual dispatch only and destruction is a first class operation.

## Stacks

| Stack | Contents | Destroy impact |
|---|---|---|
| `SignalPlane-Core-<stage>` | VPC, payload bucket, signal index, policy store | Destroys data outside `prod`; retained in `prod`. |
| `SignalPlane-Ingest-<stage>` | Adapter Lambdas, ingest API, DLQ | Safe to destroy; adapters are stateless. |
| `SignalPlane-ControlPlane-<stage>` | ECS Fargate service and load balancer | Safe to destroy; stops new sessions opening. |

Small and separable is the point. The control plane can be destroyed without losing data, and Ingest can be redeployed without touching Core.

## Cost notes

- One NAT gateway, not one per availability zone. NAT is usually the largest line item in a dev account and the availability benefit is not worth it below production.
- DynamoDB is on demand. No provisioned capacity accruing while idle.
- Fargate desired count is 1 outside production.
- `make cdk-synth` is free and needs no credentials. Use it for iteration.

## Running a deployment

Actions, then Deploy, then Run workflow. Choose the stage, then `deploy`, `diff`, or `destroy`.

The workflow uses OIDC role assumption, so no long lived AWS keys live in the repository. Configure per environment:

- Secret `AWS_DEPLOY_ROLE_ARN`
- Variable `AWS_REGION`

Deployments are serialised per stage by a concurrency group and are not cancelled in flight, because a cancelled CloudFormation update leaves a stack in a state someone has to clean up by hand.

## Before a release

Local green does not guarantee cloud green. Deploy `dev`, exercise the smoke path, destroy it. The divergences that matter are listed in `local-development.md`.
