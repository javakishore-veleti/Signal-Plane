# DevOps

| Path | Purpose |
|---|---|
| `Local/` | Docker substrate for development. Free, fast, no cloud account. |
| `Cloud/cdk/` | AWS CDK synthesizing CloudFormation. Small separable stacks. |

## Local

Each substrate is its own compose project under `Local/<Service>/`, joined by one
external Docker network. This is deliberate: Kafka can be wiped and restarted
without touching the policy store, and a misbehaving broker is a two second fix
rather than a full teardown.

```
cd DevOps/Local
./docker-all-up.sh                   # Postgres, Kafka, Redis, MinIO
./docker-all-up.sh all               # plus Observability
./docker-all-up.sh Kafka Redis       # only those
./docker-all-status.sh               # what is running and whether it is healthy
./docker-all-status.sh --json        # machine readable
./docker-all-logs.sh Kafka
./docker-all-down.sh                 # stop, keep data
./docker-all-down.sh --volumes       # stop and delete data, asks for confirmation
./docker-all-reset.sh                # destroy and rebuild from scratch
```

Ports and credentials live in `Local/.env` so they are declared once.

Health is waited on by default. The alternative is a race: services starting
against a broker that is still forming produce errors that look like
configuration problems and cost an hour to diagnose.

## Substrate mapping

| Local | Cloud | Interface depended on |
|---|---|---|
| Redpanda | Amazon MSK | Kafka protocol |
| MinIO | Amazon S3 | S3 API |
| PostgreSQL | DynamoDB | Repository interface |
| Redis | Amazon ElastiCache | Redis protocol |

Dependencies are on protocols with more than one viable implementation. The local
stack is the continuous proof that this holds; a portability claim never
exercised is not a claim.

## Where local diverges from cloud

Local success does not imply cloud success. The gaps that bite:

- **Authorisation.** Nothing local enforces least privilege. Permission errors surface on first deploy.
- **Broker authentication.** Redpanda runs plaintext; MSK uses IAM or SASL.
- **Partition behaviour.** Hot partition effects under skewed tenant distribution do not appear against PostgreSQL.
- **Object lock semantics.** MinIO supports the API but retention interacts with bucket configuration differently.
- **Cold starts and payload limits.** Not modelled locally at all.

Deploy the `dev` stage, run the smoke path, destroy it. That step is not optional
before a release.

## Cloud

```
cd DevOps/Cloud/cdk
npm install
npx cdk synth                        # free, no credentials
npx cdk deploy --context stage=dev
npx cdk destroy --all --force
```

Deployment is manual dispatch only, never on push. The default posture is nothing
running.
