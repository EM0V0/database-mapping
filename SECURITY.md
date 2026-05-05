# Security posture

This repository ships a demo-grade web stack (Vue SPA + Flask) that integrates with Large Language Models. It is deliberately **not** a certified medical device nor a guaranteed PCI/SOC-compliant platform until your organization bolts on its own governance, monitoring, SSO, VPC isolation, SIEM ingestion, retention policies, and pen-test sign-off required by procurement.

Below is how the codebase mitigates the most frequent abuse classes and where professional teams still owe additional work before treating it as tenant-facing production software.

## What we hardened in code

- **Upload & body limits** — Flask enforces `MAX_CONTENT_LENGTH`; `.xlsx` uploads are sniffed for the ZIP/OpenXML signature before calling `pandas`.
- **Workbook amplification** — `pandas.ExcelFile(...).parse(nrows=...)` caps sampled rows/columns/sheet-count so benign-but-huge spreadsheets cannot deterministically allocate multi-gigabyte DataFrames inside the mapper service.
- **Schema validation** — table/field/mapping payloads are normalized (length bounds, rejects low ASCII control chars, clamps transformation rules).
- **LLM injection awareness** — SQL generation bundles mapping rows as canonical JSON alongside explicit system instructions instructing models to interpret strings strictly as literals. This reduces *some* naive prompt injections but does **not** remove the necessity for downstream human reviewers.
- **CORS tightening** — `CORS_ALLOWED_ORIGINS` replaces the insecure default `*`; fallbacks target common localhost dev origins only.
- **Security headers & opaque server faults** — `X-Content-Type-Options`, `X-Frame-Options`, conservative `Referrer-Policy`; uncaught failures return `{ "error": "Internal server error", "reference": "<id>" }` while details stay in server logs keyed by correlation id.

## Mandatory enterprise follow-ups before customer exposure

| Area | Recommendation |
| ---- | ---------------- |
| Secrets | Store keys in KMS / managed secret vaults—not `.env` on disk—in production. Rotate quarterly. |
| Transport | TLS everywhere (`reverse proxy` terminates TLS → private upstream). Disable HTTP in prod. |
| AuthN/Z | Attach OIDC scopes or mTLS plus per-route RBAC unless the tool runs completely offline/air-gapped. |
| Abuse controls | Deploy `nginx`/`istio`/`cloud armor` rate limits, optional per-tenant quotas, IP allowlists. |
| Dependencies | Subscribe to Renovate/GitHub Dependabot; run `(pip audit && npm audit)` in CI/CD with blocking SLA. |
| Logging | Structured JSON logs, no raw PHI in logs unless contractually mandated and encrypted. Ship to SIEM. |
| Prompt data | Decide whether payloads require de-identification; treat inbound spreadsheets as HIPAA assets if regulated. |

## Coordinated vulnerability disclosure

If you find a reproducible exploit path, fork authors prefer private reports referencing commit SHA + minimized repro—do **not** open a public exploit before maintainers acknowledged.

## Disclaimer

Automated tooling (GPT-class models) hallucinates. Treat generated SQL/DML/DDL as hostile until formally reviewed inside your change-management process **and** tested against scrubbed clones of production schemas.
