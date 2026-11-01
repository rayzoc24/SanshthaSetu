# Module 1 Design — APH Pipeline

**Precondition:** Module 0 Definition of Done passes.

## Goal

Allow a Main Admin to upload an APH PDF, have the system extract structured rules via Gemini, review and edit the draft, then publish a versioned ruleset. Downstream modules read rules from the published version.

## New Migration: `0002_aph_pipeline.py`

Extends stub tables from Module 0. Never edits `0001_initial_schema.py`.
Do not re-add columns that already exist in Module 0 (`aph_versions.status`; `aph_rules.programme`, `category`, `parameter`, `operator`, `unit`, `source_page`).

### `aph_versions`
Add new columns only:
- `version_label TEXT NOT NULL` — human-readable label supplied by the admin at upload time.
- `file_key TEXT` — Cloudflare R2 object key for the uploaded PDF.
- `file_name TEXT`
- `published_at TIMESTAMPTZ`
- `published_by UUID REFERENCES users(id)`
- `effective_date DATE`
- `extraction_status TEXT DEFAULT 'none'` — `none | running | done | failed`. Replaces cache check.
- `content_hash TEXT` — sha256 of the concatenated page text used for extraction. Set at upload.
- `extraction_log JSONB` — metadata only (tokens used, finish reason, page range). Not a cache flag.
- `notes TEXT`

### `aph_pages` (new table)
Stores per-page text at upload time so extraction can resume after a cold start.
- `id UUID PK`
- `version_id UUID REFERENCES aph_versions(id) ON DELETE CASCADE`
- `page_no INTEGER NOT NULL`
- `text TEXT NOT NULL`
- `created_at TIMESTAMPTZ`
- Unique constraint: `(version_id, page_no)`.

### `aph_rules`
Add new columns only (do not re-add existing ones; drop `value` if it exists; do not add `status`):
- `parameter_key TEXT` — normalized snake_case key (e.g. `faculty_phd_count`). Links to `infrastructure_records.parameter_key`.
- `programme_key TEXT` — normalized snake_case programme identifier (e.g. `b_tech`).
- `string_value TEXT` — used when the rule value is non-numeric.
- `numeric_value NUMERIC` — used when the rule value is numeric. Nullable.
- `source_quote TEXT` — verbatim short quote from the APH page confirming this rule.
- `needs_review BOOLEAN DEFAULT FALSE` — set true if `source_quote` is not found in the stored page text.
- `is_ai_suggested BOOLEAN DEFAULT TRUE`
- `edited_by UUID REFERENCES users(id)` — set when admin edits.
- `edited_at TIMESTAMPTZ`

Rule visibility follows version status; there is no per-rule status column.
Rule PATCH / POST / DELETE only permitted while the parent version is `draft`. Published versions are immutable.

Unique constraint: `(aph_version_id, programme_key, parameter_key)`.

## Services

### `aph_service.py`
- `upload_aph(file, version_label, admin_user)` — validate PDF magic bytes and size (max 25 MB); upload to R2; store pages in `aph_pages`; compute `content_hash`; create `aph_versions` row (`extraction_status='none'`); return version id.
- `start_extraction(version_id, page_start, page_end, force, admin_user)` — enqueue as a `BackgroundTask`. Reject if `extraction_status='running'` and last update < 10 minutes ago (stale guard: allow retry after 10 min). If `force=True` and version is draft, delete existing draft rules, record audit. Set `extraction_status='running'`.
- `_run_extraction(version_id, page_start, page_end)` — load `aph_pages` rows for the range; call `gemini_service.extract_aph_rules`; validate each `AphRuleDraft`; verify `source_quote` appears in stored page text (set `needs_review=True` if not); insert rules and set `extraction_status='done'` in one transaction. On error: set `extraction_status='failed'`.
- `update_rule(rule_id, payload, admin_user)` — reject if version is published; patch rule; set `edited_by`, `edited_at`, `is_ai_suggested=False`.
- `delete_rule(rule_id, admin_user)` — reject if version is published; delete row; record audit.
- `publish_version(version_id, effective_date, admin_user)` — reject if `extraction_status != 'done'`; set version `status='published'`, `published_at`, `published_by`. Record audit. Only Main Admin. Published versions are immutable.

### `gemini_service.py`
- `extract_aph_rules(text: str, page_start: int, page_end: int) -> list[AphRuleDraft]` — call Gemini Flash with structured JSON schema output, temperature 0, 30 s timeout, at most 2 retries. Validate with Pydantic `AphRuleDraft`. On failure: raise `ExtractionError` with details; never accept partial data silently.
- `AphRuleDraft` fields: `parameter`, `parameter_key`, `programme`, `programme_key`, `category`, `operator`, `string_value`, `numeric_value`, `unit`, `source_page`, `source_quote`.

### `pdf_service.py`
- `extract_pages(file_path: str) -> list[tuple[int, str]]` — PyMuPDF page-by-page extraction; returns `[(page_no, text), ...]`.

## API Endpoints (`/aph`)

Static paths defined before parameterized ones to avoid FastAPI route shadowing.

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/versions/published` | any authenticated | Latest published version (greatest `effective_date` ≤ today) |
| GET | `/versions` | main_admin | List all versions with `extraction_status` |
| POST | `/versions` | main_admin | Upload PDF + `version_label`; returns version id immediately |
| GET | `/versions/{id}` | main_admin | Single version detail including `extraction_status` and `content_hash` |
| GET | `/versions/{id}/pdf-url` | main_admin | Signed R2 URL (short TTL, generated on demand) |
| POST | `/versions/{id}/extract` | main_admin | Start extraction (`?page_start=&page_end=&force=true`); returns immediately |
| GET | `/versions/{id}/rules` | main_admin | List all rules for a version (includes `needs_review`, `is_ai_suggested`) |
| POST | `/versions/{id}/rules` | main_admin | Add a manual rule to a draft version |
| PATCH | `/rules/{rule_id}` | main_admin | Edit a single rule (draft version only) |
| DELETE | `/rules/{rule_id}` | main_admin | Delete a rule (draft version only) |
| POST | `/versions/{id}/publish` | main_admin | Publish version with `effective_date` |

`GET /versions/published` returns the published `aph_version` with the greatest `effective_date` that is not in the future (i.e. `effective_date <= today`). Must be defined before `GET /versions/{id}` in the router.

## Extraction Flow

1. `POST /versions` — validate, upload to R2, store pages in `aph_pages`, compute `content_hash`, set `extraction_status='none'`.
2. `POST /versions/{id}/extract?page_start=1&page_end=15` — reject if `running` and updated < 10 min ago; if `force=true` and draft, delete existing rules (audited); set `extraction_status='running'`; enqueue background task; return `{extraction_status: "running"}`.
3. Background task `_run_extraction` — loads `aph_pages`, calls Gemini, validates, checks `source_quote`, inserts rules and sets `extraction_status='done'` in one transaction. On error: sets `extraction_status='failed'`.
4. UI polls `GET /versions/{id}` until `extraction_status` is `done` or `failed`.
5. If content hash matches a previously completed version, return cached rules immediately without calling Gemini.

## Audit Events

`upload_aph`, `start_extraction`, `force_reextract`, `add_rule`, `edit_aph_rule`, `delete_aph_rule`, `publish_aph_version`.

## File Storage

PDF uploaded to R2 bucket under `aph/{version_id}/{file_name}`. Signed URL generated on demand (never stored in DB).

## Out of Scope

- Multi-file APH upload.
- Diff view between versions.
- Bulk rule import from CSV.
