# Local development

Iterating on this platform should cost nothing. Cloud managed services are the deployment target, but a system that can only be run by paying for a live account is one contributors avoid running (ADR-0010).

## Substrate

| Local | Cloud | Interface depended on |
|---|---|---|
| Redpanda | Amazon MSK | Kafka protocol |
| MinIO | Amazon S3 | S3 API |
| PostgreSQL | DynamoDB | Repository interface in application code |

Services depend on the protocol, never on a vendor SDK feature with no local equivalent.

```bash
make up      # start everything
make seed    # demo tenant, subjects, jurisdiction policy
make demo    # adapter run end to end
make clean   # stop and delete all local state
```

## What runs today

| Component | State |
|---|---|
| Schemas and taxonomy | Complete. `make validate` cross checks them. |
| Adapter library | Complete, with contract tests covering determinism, hash chaining, and fail closed behaviour. |
| Reference adapter | Runs end to end, with or without a broker present. |
| Query broker | Complete with tests, backed by a stub estate. Swap `StubEstate` for an index backed implementation without touching `Broker`. |
| Edge shipper | Complete, reads from a spool directory. |
| Control plane | Authority gate and its HTTP surface are real. `PolicyRepository` needs a JDBC implementation. |
| Console | Scaffold only. |

## Running without any infrastructure

The adapter falls back to stdout when no broker is configured, so the envelope path can be exercised with nothing installed:

```bash
python3 -m adapters.python.sources.directory_watch.handler --once --root /tmp/watch
```

The authority client behaves the same way: with no `CONTROL_PLANE_URL` set it issues a local decision that is still time bounded, so the offline path exercises expiry and fail closed handling rather than skipping them.

## Where local diverges from cloud

Local green does not guarantee cloud green. The known gaps:

- **IAM.** Nothing local enforces least privilege. Permission errors surface only on first deploy.
- **MSK authentication.** Redpanda runs plaintext; MSK uses IAM or SASL.
- **DynamoDB partition behaviour.** Hot partition effects under a skewed tenant distribution do not appear against PostgreSQL.
- **S3 object lock.** MinIO supports the API but retention interacts with bucket configuration differently.
- **Lambda cold starts and payload limits.** Not modelled locally at all.

Deploy the `dev` stage, run the smoke path, and destroy it before a release. That step is not optional.

## Adding an adapter

1. Create `adapters/python/sources/<name>/` with a `manifest.json` and a `handler.py`.
2. Add any new `signal_type` values to `taxonomy.yaml`. Additive only.
3. Map source events using `AdapterContext.build`. Do not construct envelopes by hand; identity, hashing, and fail closed checks live in the shared library for a reason.
4. `make validate` must pass. It fails if a manifest emits a signal type the taxonomy does not know about.
5. Register the Lambda in `infra/cdk/lib/ingest-stack.ts`. Nothing else changes, which is the property the architecture is buying.
