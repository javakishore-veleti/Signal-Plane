# Portals

Angular applications. Two audiences with different obligations, sharing a
contract layer.

| Portal | Audience | Purpose |
|---|---|---|
| `admin-portal` | Platform and tenant administrators | Policy, scope, retention, adapter registry, migration state |
| `client-portal` | Investigators and compliance owners | Signal timelines, case views, provenance, export |
| `shared` | Both | Generated contract models, API clients, estate status handling, design system |

## Scaffolding

From this directory:

```
npx @angular/cli@18 new admin-portal  --routing --style=scss --skip-git --standalone
npx @angular/cli@18 new client-portal --routing --style=scss --skip-git --standalone
npx @angular/cli@18 generate library shared --project-root shared
```

## Dev proxy

Each portal needs a `proxy.conf.json` routing to the middleware services so the
dev server avoids CORS:

| Path | Target | Service |
|---|---|---|
| `/v1/signals` | `http://localhost:8081` | Query broker |
| `/v1/authority` | `http://localhost:8080` | Control plane |
| `/v1/sessions` | `http://localhost:8080` | Control plane |
| `/v1/subjects` | `http://localhost:8080` | Control plane |
| `/v1/adapters` | `http://localhost:8080` | Control plane |

Run with `ng serve --proxy-config proxy.conf.json`.

## Two obligations that are architectural, not cosmetic

**Degradation is displayed.** The query broker returns a per estate status array
and sets a partial results header when any estate failed to answer. Both portals
must render a banner naming the unavailable estate and must qualify result
counts. A console that silently returns half the data during an investigation is
worse than one that returns an error, because the investigator has no signal
that anything is missing.

**Scope is reflected, not enforced.** Group and user filters are a convenience.
Enforcement is structural at the data layer. The portal must never present a
scope selection the caller does not actually hold, because a control that exists
only in the interface is not a control.

## Contract models

Types are generated from `Contracts/schemas` rather than hand written, so a
contract change surfaces as a compile error in the portal rather than as a
runtime surprise. Generation belongs in `shared`, and the generated output is
committed so that a fresh clone builds without a code generation step.
