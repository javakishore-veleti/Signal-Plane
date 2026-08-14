-- Local policy store. In the cloud this is DynamoDB; the shape is the same.
-- Everything is keyed by tenant first, so a query that forgets tenant scoping
-- fails to compile rather than leaking.

CREATE TABLE IF NOT EXISTS tenant (
  tenant_id            TEXT PRIMARY KEY,
  name                 TEXT NOT NULL,
  scoring_model_version TEXT NOT NULL,   -- pinned per tenant, see ADR-0009
  estate               TEXT NOT NULL DEFAULT 'managed',
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS subject (
  tenant_id    TEXT NOT NULL REFERENCES tenant(tenant_id),
  subject_id   TEXT NOT NULL,
  jurisdiction TEXT NOT NULL,            -- governs capture, follows the subject
  PRIMARY KEY (tenant_id, subject_id)
);

CREATE TABLE IF NOT EXISTS subject_identifier (
  tenant_id  TEXT NOT NULL,
  kind       TEXT NOT NULL,
  value      TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  confidence NUMERIC NOT NULL DEFAULT 1.0,
  PRIMARY KEY (tenant_id, kind, value)
);

CREATE TABLE IF NOT EXISTS jurisdiction_policy (
  jurisdiction         TEXT PRIMARY KEY,
  policy_version       TEXT NOT NULL,
  permitted_modes      TEXT[] NOT NULL,
  approver_override    TEXT,
  basis                TEXT NOT NULL,
  max_lifetime_seconds INT NOT NULL,
  excluded_destinations TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS approval (
  tenant_id    TEXT NOT NULL,
  subject_id   TEXT NOT NULL,
  capture_mode TEXT NOT NULL,
  approver     TEXT NOT NULL,
  recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  evidence_ref TEXT,
  PRIMARY KEY (tenant_id, subject_id, capture_mode, approver)
);

CREATE TABLE IF NOT EXISTS adapter_registration (
  adapter_id TEXT NOT NULL,
  version    TEXT NOT NULL,
  manifest   JSONB NOT NULL,
  PRIMARY KEY (adapter_id, version)
);

-- Demo data
INSERT INTO tenant VALUES ('tenant-demo', 'Demo tenant', 'scoring-1.4.0', 'managed')
  ON CONFLICT DO NOTHING;

INSERT INTO jurisdiction_policy VALUES
  ('US-NC', 'policy-2026.3', ARRAY['passive_metadata','content_capture','triggered_screen','continuous_screen'],
   NULL, 'notice', 3600, ARRAY['*.bank.example','*.health.example']),
  ('DE',    'policy-2026.3', ARRAY['passive_metadata'],
   'works_council', 'consent', 1800, ARRAY['*.bank.example','*.health.example','*.union.example'])
  ON CONFLICT DO NOTHING;

INSERT INTO subject VALUES
  ('tenant-demo', 'subject-0001', 'US-NC'),
  ('tenant-demo', 'subject-0002', 'DE')
  ON CONFLICT DO NOTHING;

INSERT INTO approval (tenant_id, subject_id, capture_mode, approver) VALUES
  ('tenant-demo', 'subject-0001', 'passive_metadata', 'employer'),
  ('tenant-demo', 'subject-0001', 'continuous_screen', 'subject'),
  ('tenant-demo', 'subject-0002', 'passive_metadata', 'works_council')
  ON CONFLICT DO NOTHING;
