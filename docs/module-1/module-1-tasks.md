# Module 1 Tasks: APH Pipeline

**Precondition:** Module 0 Definition of Done passes, and Module 0.5 (UI theme) is merged.
**Read first:** context.md, docs/engineering-rules.md, docs/module-1/design.md. Where this file and design.md differ, design.md wins.
**Approved libraries for this module (no need to ask):** PyMuPDF, boto3, google-genai, python-multipart.
**Routes are unprefixed** (`/aph/...`), matching Module 0.
**Tests:** every endpoint needs tests for wrong role (403), missing token (401), and the happy path. Gemini is always replaced by a fake client in automated tests; the real API is only called in manual steps (Task 8).

---

### Task 1: Dependencies, environment, storage and Gemini clients
Add the approved libraries to requirements. Add env vars to `.env.example`: R2 endpoint URL, access key, secret key, bucket name; `GEMINI_API_KEY`, `GEMINI_MODEL`. Create `services/storage_service.py` (upload object, signed URL, delete) and a thin `services/gemini_client.py` wrapper (timeout, max 2 retries) that can be swapped for a fake in tests.
Deliverable: settings, `.env.example`, both service files.
AC: a manual script uploads a small file to R2 and fetches a signed URL that downloads it; no secret appears in logs or git.

### Task 2: Migration `0002_aph_pipeline.py`
Follow design.md exactly. Add only NEW columns. Do not re-add columns that already exist from `0001`. Drop `aph_rules.value`; add `string_value` and `numeric_value`. Add `aph_pages` table, `extraction_status`, `content_hash`, `programme_key`, `source_quote`, `needs_review`. Unique constraint `(aph_version_id, programme_key, parameter_key)`. No `aph_rules.status` column.
Deliverable: `alembic/versions/0002_aph_pipeline.py`, updated models.
AC: upgrade, `downgrade -1`, upgrade succeeds on a clean DB; `\d aph_rules` shows no duplicated columns.

### Task 3: Upload, page storage and version endpoints
`POST /aph/versions` (main_admin): multipart with `version_label` and PDF. Validate PDF magic bytes and a 25 MB limit. Upload to R2, extract text per page with PyMuPDF into `aph_pages`, create the draft version. Also `GET /aph/versions` (list), `GET /aph/versions/{id}`, `GET /aph/versions/{id}/pdf-url` (signed URL, never stored).
Deliverable: router, `aph_service.upload_aph`, `pdf_service.extract_pages`, tests.
AC: stored page rows equal the PDF page count; a non-PDF returns 400; an oversize file returns 400; audit rows exist for upload.

### Task 4: Gemini extraction service (no endpoint yet)
`gemini_service.extract_aph_rules(pages_text)` with the prompt in its own file. Use Gemini structured output (JSON schema), temperature 0. Validate with Pydantic `AphRuleDraft` (including `source_quote`). Maximum 15 pages per call. On failure raise `ExtractionError`; never return partial data.
Deliverable: `services/gemini_service.py`, `AphRuleDraft`, prompt file, tests.
AC: with a fake client, a valid fixture yields rule objects; a malformed response, a missing field, and a timeout each raise `ExtractionError`.

### Task 5: Extraction orchestration and endpoint
`POST /aph/versions/{id}/extract` with `page_start`, `page_end`, optional `force`. Runs as a background task and returns immediately. Statuses: none, running, done, failed. Cache by `content_hash` of the selected pages. Insert rules and set `done` in one transaction. After extraction, verify each `source_quote` appears on its `source_page`; if not, set `needs_review`. `force` is allowed only while the version is draft, replaces draft rules, and is audited. A `running` status older than 10 minutes may be retried.
Deliverable: orchestration in `aph_service`, route, tests.
AC: a second call with the same range makes zero Gemini calls (fake client counter); a failed extraction stores no rules and sets `failed`; `force` replaces the rules and writes an audit row; status is readable via `GET /aph/versions/{id}`.

### Task 6: Rule endpoints
`GET /aph/versions/{id}/rules` (paginated, filters: `programme_key`, `needs_review`), `POST /aph/versions/{id}/rules`, `PATCH /aph/rules/{id}`, `DELETE /aph/rules/{id}`. All writes only while the version is draft. Edits set `edited_by`, `edited_at` and `is_ai_suggested = false`. Duplicate key returns 409; writes to a published version return 409.
Deliverable: routes, schemas, tests.
AC: the AI-suggested flag shows in GET and clears after PATCH; each endpoint is audited and tested for 403 and 401.

### Task 7: Publish endpoints
`POST /aph/versions/{id}/publish` with `effective_date` (main_admin). Blocked if the version has no rules, or if any rule still has `needs_review`. Published versions are immutable. `GET /aph/versions/published` returns the published version with the greatest `effective_date` not in the future (define this route before parameterized routes).
Deliverable: `publish_version`, routes, tests.
AC: publishing twice returns 409; publishing with a flagged rule returns 400 with the rule ids; the audit row exists; college_admin gets 403 on publish but can read `GET /aph/versions/published`.

### Task 8: Real-data validation and demo seed (partly manual)
Run extraction on 10 to 15 real pages of the public APH. Review every rule by hand, and record the result (rules found, rules correct, rules corrected, rules missed) in `docs/module-1/extraction-notes.md`. Save the verified ruleset as `seed_aph_demo.py`, an idempotent script that creates a published version with its rules, so the demo works without live Gemini.
Deliverable: notes file, seed script.
AC: the seed creates a published version with its rules; notes contain accuracy numbers; the seed runs twice without duplicates.

### Task 9: Frontend, upload, extract and version list
`/admin/aph` lists versions with status. `/admin/aph/upload` has the label field, file picker and upload. After upload show page-range inputs and an Extract button, poll status every 3 seconds, show error details on failure, and show a "server may be waking up" message on slow responses. Use theme tokens only.
Deliverable: `APHVersionsPage.tsx`, `APHUploadPage.tsx`.
AC: the full flow works against the real API; the failure state shows the `ExtractionError` detail.

### Task 10: Frontend, review and publish
`/admin/aph/{id}/rules`: rules table with an **AI-suggested** badge, a visible "needs review" warning, inline edit, add and delete rule, and a link that opens the source PDF page via the signed URL. The Publish button with date picker is disabled while any rule needs review. Redirect to the version list after publishing.
Deliverable: `APHRulesPage.tsx`.
AC: editing clears the badge; publish works; roles other than main_admin cannot reach the page.

---

## Definition of Done

- [ ] `0002` applies cleanly and round-trips.
- [ ] Upload, extraction (cached by content hash), review, and publish work end to end.
- [ ] Zero Gemini calls on repeated extraction of the same range.
- [ ] Every endpoint has 401 and 403 tests; audit rows exist for upload, extract, edit, delete, publish.
- [ ] Published versions cannot be changed.
- [ ] Extraction notes record real accuracy on real APH pages.
- [ ] Demo ruleset is seeded and works without live Gemini.
- [ ] AI values are labeled in the UI; nothing is auto-published.
- [ ] No mock data in the frontend.

## Deployment Checkpoint

Deploy to Render and Vercel. On the live URLs, run upload, extract, edit and publish. Check three things that often break only in production: multipart upload through CORS, the Render cold start during extraction polling, and signed-URL downloads from R2. Confirm the audit rows in Neon.

## Note for Module 2

The readiness comparison needs each college programme mapped to a rule `programme_key`. Module 2's design must define that mapping.
