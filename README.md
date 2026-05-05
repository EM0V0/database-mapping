# Database Mapping Workbench

Modernized demo that pairs a Vue 3 interface with a Flask service to visually map columns between heterogeneous sources and a canonical target definition. OpenAI-compatible models recommend sheet coverage, align fields, and draft SQL you can review before running any migration.

## Highlights

- **Guided AI flows** with English prompts, strict JSON parsing, and Markdown fence stripping for safer automation.
- **RESTful Flask API** with health checks, structured error JSON, and temporary upload handling (no `subprocess` orchestration).
- **Developer-friendly Vue layer** that targets same-origin `/api/*` routes (with a fixed webpack dev proxy) or an optional `VUE_APP_API_ORIGIN` override.
- **Environment-driven secrets** via `python-dotenv` — no more empty API keys committed in code.

## Architecture

```
project-root/
├── src/
│   ├── api/client.js            # fetch helpers + env-aware base URLs
│   └── components/
│       ├── MappingTool.vue
│       ├── SourceTableUpload.vue
│       ├── TargetTableUpload.vue
│       └── TableComponent.vue
├── backend/
│   ├── app.py                   # Flask entrypoint
│   ├── ai_pipeline.py           # OpenAI orchestration + parsing utilities
│   ├── config.py                # Environment configuration
│   ├── validators.py            # Structural schema + identifier guards
│   ├── tests/                   # pytest safety net (runs in CI without OpenAI egress)
│   ├── requirements.txt
│   └── .env.example
├── package.json
├── .github/
│   └── workflows/
│       └── ci.yml
└── vue.config.js
```

## Prerequisites

- Node.js 18+ and npm 9+
- Python 3.10+ (**align `python -m pip` with the interpreter you run** — Windows often exposes multiple interpreters)
- An OpenAI API key (or any OpenAI-compatible endpoint that supports `chat.completions`)

## Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Optional: only needed to run pytest locally or match CI.
python -m pip install -r requirements-dev.txt
copy .env.example .env
notepad .env   # add OPENAI_API_KEY (and optional OPENAI_BASE_URL / OPENAI_MODEL)
python app.py
```

The API listens on `http://127.0.0.1:5000`. Quick smoke test:

```powershell
curl http://127.0.0.1:5000/api/health
```

### Environment variables

| Name | Required | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | Secret used by the OpenAI Python client. |
| `OPENAI_BASE_URL` | No | Custom base URL for OpenAI-compatible gateways. |
| `OPENAI_MODEL` | No | Defaults to `gpt-4o`. Pick a model that fits your provider. |
| `MAX_UPLOAD_MB` | No | Flask `MAX_CONTENT_LENGTH` safeguard (defaults to 25 MB). |
| `MAX_LLM_PROMPT_CHARS` | No | Clamp for serialized payloads posted to GPT-style APIs. |
| `LLM_REPAIR_ATTEMPTS` | No | Retry rounds after programmatic validation failure (maps, sheets, SQL). Default `2`, capped at 8. |
| `LLM_TEMP_STRUCTURE` | No | Temperature for JSON-heavy steps (sheet list, mappings). Default `0.12`. |
| `LLM_TEMP_SQL` | No | Temperature for SQL drafting. Default `0.22`. |
| `CORS_ALLOWED_ORIGINS` | No | CSV allowlist (`http(s)://host:port`). Empty → localhost dev presets. Literal `*` is sandbox-only. |

## Frontend setup

```powershell
cd ..
npm install
npm run serve
```

By default the dev server proxies `/api/*` to Flask, so you can keep `VUE_APP_API_ORIGIN` unset. If you host the UI separately, create `.env.development.local`:

```
VUE_APP_API_ORIGIN=http://127.0.0.1:5000
```

## REST surface

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness probe for orchestrators. |
| `POST` | `/api/recommend` | Multipart `source_file` (`.xlsx`) + `target_file` (JSON table) → ranked sheet names. |
| `POST` | `/api/recommend_fields` | Multipart JSON arrays describing every loaded source table + selected target table → mapping rows. |
| `POST` | `/api/generate_sql` | JSON body mirroring the UI (`fieldMappings`) → generated SQL string. |

## Working with the UI

1. Import a target definition (`TargetTableUpload`) as JSON: `[{ "name": "...", "fields": [{ "name": "...", "comment": "..." }] }]`.
2. Import an Excel workbook (`SourceTableUpload`). First row = column names, optional second row = human comments.
3. Select tables on both sides, drag fields to connect them, and iterate with **Recommend Field Mappings** / **Generate SQL**.
4. Export/import mapping JSON for collaboration.

## Automated verification

```powershell
cd backend
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests -q

cd ..
npm ci
npm run lint
npm run build
```

GitHub Actions (`.github/workflows/ci.yml`) runs the same toolchain on pushes/PRs: pytest, ESLint, production bundle, advisory `pip-audit`/`npm audit` steps (warnings are surfaced but do not permanently block merges while legacy Vue CLI transitive issues remain).

Consult `SECURITY.md` for residual enterprise obligations (IAM, KMS, PHI handling, SSE, etc.). This repository deliberately stops short of HIPAA/FedRAMP attestation—you still own formal risk assessments.

## Demo fixtures for UI testing

Synthetic but detailed files live in `fixtures/`:

- `fixtures/std_patient_clinical_hub.json` — **standard target catalog** (single table, 52 fields, English identifiers + descriptions). Copied beside the XLSX under `public/fixtures/` when you run the generator. Import manually if you prefer — **during `npm run serve` the UI also auto-loads both files on startup** (`MappingTool.vue`).
- `fixtures/demo_hospital_ehr_messy_multi_sheet.xlsx` — **hospital-style source** workbook (two sheets). The generator also copies artifacts into **`public/fixtures/`** so the dev SPA can preload them without manual uploads. Regenerate anytime with `python fixtures/build_hospital_ehr_demo_xlsx.py` from the repo root (needs `openpyxl`; backend `requirements.txt` includes it).

**Run the stack for manual testing:** Terminal A — `cd backend`, activate venv, `python app.py`. Terminal B — `npm run serve`, open the printed local URL; the dev server proxies `/api` to `http://127.0.0.1:5000`.

## Testing checklist

- Upload representative Excel + JSON fixtures and confirm tables render.
- Exercise drag-and-drop mapping lines (D3 overlay) while scrolling both panes.
- Run each AI endpoint once with a valid API key and verify JSON/SQL output quality.
- Toggle `VUE_APP_API_ORIGIN` to simulate split hosting.

## Operational notes

- AI output is **assistive** — review every mapping and SQL statement before production loads.
- Temporary uploads land in `backend/uploads/`, which is git-ignored. Clear it periodically on shared machines.
- The legacy `workflow*.py` scripts were removed in favor of importable functions inside `ai_pipeline.py`.

## Credits

Original concept and Chinese documentation by Andy Sun (July 2024). This fork modernizes the stack, localizes documentation, and hardens the integration layer.
