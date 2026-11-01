# Module 2 Tasks — Institutional Data & Readiness Assessment

**Preconditions**
- Module 0 Definition of Done passes.
- Module 0.5 UI theme is merged.
- Module 1 Definition of Done passes, or fixture data provides at least one published `aph_version` with verified rules.
- Published APH rules have stable `programme_key` and `parameter_key` values.
- Read `context.md`, `docs/engineering-rules.md`, and `docs/module-2/design.md` before implementation. If this task file and `design.md` differ, `design.md` wins.
- Reuse Module 1 storage, PDF extraction, Gemini client, authentication, audit, and API conventions. Do not duplicate infrastructure.

**Objective:** Build the college institutional profile and readiness assessment capability. College Admins provide infrastructure information through structured forms and optional document uploads. The system compares verified college information against applicable rules in the published APH version and produces traceable readiness reports.

**Core principle:** AI may extract and suggest information, but it must not silently verify institutional facts or certify statutory compliance. College Admins verify submitted information. Readiness results are advisory; authorized officials and inspection committees retain statutory decision-making authority.

**Approved libraries:** Reuse the fixed project stack and Module 1 approved libraries. Do not add dependencies without approval. Module 1 approved libraries include PyMuPDF, boto3, google-genai, and python-multipart.

---

## Task 1 — Migration `0003_readiness_assessment.py`

Create the schema for institutional information, evidence provenance, programme mapping, and readiness snapshots.

**Requirements**
- Inspect actual Module 0 and Module 1 models/migrations first. Add only missing fields; do not duplicate existing fields.
- Extend the existing `infrastructure_records` stub as specified in `docs/module-2/design.md`.
- Create `readiness_snapshots` and `readiness_items`.
- Scope infrastructure records by institution, APH version, `programme_key`, and `parameter_key`.
- Track record provenance and verification:
  - `source_type`: `form` or `uploaded_document`
  - `source_document_id`: nullable reference to source document
  - `verification_status`: `pending`, `verified`, or `rejected`
  - `verified_by`: nullable user reference
  - `verified_at`: nullable timestamp
- Snapshots preserve institution, APH version, programme, assessment timestamp, summary counts, and individual rule outcomes.
- Add appropriate foreign keys, indexes, and uniqueness constraints.
- Use Alembic for every schema change. Never edit tables manually.

**Deliverable**
- `alembic/versions/0003_readiness_assessment.py`
- Updated SQLAlchemy models and required schemas.

**Acceptance criteria**
- `alembic upgrade head` succeeds on a clean database.
- `alembic downgrade -1` followed by `alembic upgrade head` succeeds.
- The unique constraint on institution + APH version + programme + parameter rejects duplicate records.
- No columns or constraints are duplicated.

---

## Task 2 — Infrastructure record upsert endpoint

Implement `POST /api/v1/readiness/records`.

**Authorization and requirements**
- College Admin only.
- Derive institution identity from the authenticated user's authorized institution context wherever possible; never trust a client-supplied institution ID.
- A College Admin cannot create or update records for another institution.
- Upsert using institution + APH version + programme + parameter as the logical scope.
- Validate that the APH version exists and is published.
- Validate that programme and parameter keys exist in that version and are applicable to the institution's programme mapping.
- Validate value type and unit against the APH rule. Do not silently coerce incompatible values.
- Form-entered values use `source_type=form`.
- New or changed values must not become verified automatically unless the College Admin explicitly confirms them through the defined verification flow.
- Audit successful creates and updates.

**Deliverable**
- `routers/readiness.py`
- Upsert function in `services/readiness_service.py`
- Request/response schemas.

**Acceptance criteria**
- College Admin can create and update a record for their own institution.
- Cross-institution access returns `403`.
- Invalid/unpublished APH versions and unknown programme/parameter keys are rejected consistently.
- Audit row is created for each successful create/update.
- Tests cover missing token (`401`), wrong role (`403`), and happy path.

---

## Task 3 — Programme mapping

Implement mapping between each institution's programmes and APH `programme_key` values.

**Requirements**
- An institution may offer multiple programmes.
- Each institution programme maps to an applicable APH `programme_key`.
- Do not infer mappings from similar-looking names without an explicit, reviewable mapping.
- Validate that a mapping points to a `programme_key` present in the selected published APH version.
- Readiness comparison evaluates only rules relevant to the institution's mapped programmes.
- Preserve the mapping used by a snapshot so later mapping changes do not rewrite historical results.

**Deliverable**
- Programme mapping model/schema changes if required by `design.md`.
- Required API endpoints and service functions.
- Tests for valid mappings, invalid keys, and institution-level authorization.

**Acceptance criteria**
- A college with multiple programmes can map each programme independently.
- Rules for unrelated programmes are excluded from its assessment.
- Invalid or ambiguous mappings cannot silently pass.
- Mapping changes are audited.
- Endpoint tests cover `401`, `403`, and happy path.

---

## Task 4 — Comparison logic (unit-tested)

Implement `readiness_service.compare(institution_id, aph_version_id, programme_key)`. The signature may follow `design.md`, but comparison must be deterministic and independently unit-testable.

**Requirements**
- Load published APH rules applicable to the institution's mapped programme(s).
- Compare numeric and string values using each rule's operator.
- Respect units and supported operators. Never silently coerce incompatible values.
- No corresponding institutional record => `missing`.
- Present record that is pending verification, rejected, or lacks required evidence => `needs_verification`.
- Verified record satisfying the rule => `met`.
- Verified record not fully satisfying the rule => `partial` or `missing`, according to semantics defined in `design.md`.
- Return structured `ReadinessItemResult` objects with at least `parameter_key`, `programme_key`, `status`, `required`, `actual`, `unit`, and `gap_description`.
- Unit tests must not call Gemini or require a live database.

**Statuses**
- `met`
- `partial`
- `missing`
- `needs_verification`

**Deliverable**
- Comparison function in `readiness_service.py`
- `ReadinessItemResult` schema
- Unit tests with synthetic rule/record fixtures.

**Acceptance criteria**
- Tests cover numeric and string operators and all four statuses.
- Missing records never appear as met.
- Unverified AI-extracted information never appears as met.
- Unsupported operators, invalid values, and incompatible units produce explicit errors or review states; never silently pass.
- Unit tests pass without database access.

---

## Task 5 — Readiness snapshot endpoint

Implement `POST /api/v1/readiness/snapshots`.

**Authorization and requirements**
- College Admin only; derive institution from authenticated user context.
- Accept target published APH version and programme scope, or assess all mapped programmes if explicitly requested.
- Call the comparison service.
- Persist a `readiness_snapshot` and associated `readiness_items` in one transaction.
- Snapshots are immutable records of the assessment at that point in time.
- Store APH version, programme mapping used, assessment timestamp, required/actual values, statuses, and gap descriptions.
- Return counts for `total`, `met`, `partial`, `missing`, and `needs_verification`.
- Audit snapshot generation.
- Label the result advisory; it is not official AICTE certification or approval.

**Deliverable**
- Snapshot creation route and persistence logic.

**Acceptance criteria**
- Response includes all five summary counts.
- Snapshot and item rows exist in the database.
- Later infrastructure updates do not alter an existing snapshot.
- Wrong role returns `403`; missing token returns `401`.
- Audit row exists for snapshot generation.

---

## Task 6 — Gap report detail endpoint

Implement `GET /api/v1/readiness/snapshots/{id}`.

**Authorization and data scoping**
- College Admin: own institution's snapshots only.
- Regional Officer: institutions in their authorized region only.
- Main Admin: access according to Module 0 administrative permissions.
- Other roles are denied unless explicitly authorized by the design.

**Response fields**
Return summary and full item list, including `parameter_key`, `programme_key`, `status`, `required`, `actual`, `unit`, `gap_description`, and relevant source/verification information.

**Deliverable**
- Detail route with role-aware institution and region scoping.

**Acceptance criteria**
- College Admin cannot view another institution's snapshot.
- Regional Officer cannot view a snapshot from another region.
- Authorized users receive all items with correct statuses.
- Missing token returns `401`; unauthorized role/scope returns `403`.
- Tests cover applicable roles and happy path.

---

## Task 7 — Frontend: infrastructure data entry

Page: `/college/readiness/enter`

**Requirements**
- College Admin only.
- Load active published APH version and institution's mapped programmes from the real API.
- Display applicable APH parameters grouped by programme/category.
- Provide input appropriate to each rule's data type and unit.
- Save each record through the upsert endpoint.
- Show unsaved, saved, pending verification, verified, or rejected state.
- Distinguish manually entered information from AI-extracted suggestions.
- No mock data; all displayed records come from the backend.

**Deliverable**
- `InfrastructureEntryPage.tsx`

**Acceptance criteria**
- Saved records appear in the real records API.
- Unsaved rows are visually distinguishable.
- Validation errors appear beside the relevant field.
- College Admin cannot access another institution's data.
- Existing theme tokens and shared UI components are used.

---

## Task 8 — Document upload and AI-assisted extraction

Build optional document-based institutional data collection.

**Requirements**
- College Admin can upload relevant institutional documents, initially PDF.
- Reuse Module 1 Cloudflare R2 storage and PyMuPDF extraction services. Do not duplicate them.
- Validate file type, PDF signature, size, and malformed/encrypted PDF cases.
- Store document metadata and institution ownership. Use private object storage and signed URLs; never expose permanent public URLs.
- Extract relevant infrastructure facts using the existing Gemini client with a separate version-controlled prompt and Pydantic response schema.
- Map extracted facts only to known `programme_key` and `parameter_key` values.
- Preserve source document and page references for every suggestion.
- Unknown or ambiguous facts are surfaced for manual mapping; do not invent mappings.
- Mark extracted values as AI-suggested and pending verification.
- College Admin can review, edit, accept, or reject each suggestion before it becomes a verified infrastructure record.
- Cache extraction results for unchanged document content.
- Audit uploads and relevant review actions.
- Automated tests use a fake Gemini client; real Gemini calls are only for manual validation.

**Deliverable**
- Document upload/extraction routes and services.
- Required document metadata and extraction models/schemas.
- Separate prompt file.
- Tests for upload, extraction, mapping, review, authorization, and failure handling.
- Frontend upload/review components integrated into infrastructure entry.

**Acceptance criteria**
- College Admin can upload a document belonging to their institution.
- Another institution's document cannot be read or modified.
- Valid facts are returned as AI suggestions with source-page references.
- Unknown facts are not silently mapped.
- No suggestion is treated as verified before College Admin confirmation.
- Tests cover `401`, `403`, happy path, and fake Gemini behavior.

---

## Task 9 — Frontend: readiness report

Page: `/college/readiness/report`

**Requirements**
- College Admin only.
- Provide programme selector and option to assess all mapped programmes.
- "Run Assessment" calls the snapshot endpoint.
- Render counts for met, partial, missing, and needs verification.
- Display all items with required value, actual value, unit, status, and gap description.
- Status styling: met (green), partial (amber), missing (red), needs verification (informational warning).
- Allow authorized users to open relevant source evidence.
- Show APH version and assessment timestamp.
- Explain that this is an advisory readiness assessment, not official approval or statutory certification.
- No mock data.

**Deliverable**
- `ReadinessReportPage.tsx`

**Acceptance criteria**
- Assessment runs against the real API and displays all items.
- All four statuses render correctly.
- Programme filtering works.
- Historical snapshots remain viewable after infrastructure records change.
- Existing theme tokens are used.

---

## Task 10 — End-to-end verification and demo seed

**Requirements**
- Create/update an idempotent demo seed for a synthetic institution with multiple programmes, mapped programme keys, infrastructure records, and sample document metadata where appropriate.
- Seed must use a published APH version and valid rule keys.
- Do not include real personal or institutional data.
- Test this workflow:
  1. College Admin opens readiness entry.
  2. College Admin enters information through forms.
  3. College Admin optionally uploads a PDF.
  4. AI suggestions are reviewed and confirmed/rejected.
  5. College Admin runs readiness assessment.
  6. System creates an immutable snapshot.
  7. College Admin views the gap report.
  8. Regional Officer sees only snapshots in their region.
- Record results and known limitations in `docs/module-2/readiness-validation-notes.md`.

**Deliverable**
- Idempotent demo seed/update.
- `docs/module-2/readiness-validation-notes.md`
- End-to-end tests and deployment verification notes.

**Acceptance criteria**
- Seed can run repeatedly without duplicates.
- Full workflow works against real database and APIs.
- No frontend mock data.
- Relevant endpoints test missing token (`401`), wrong role (`403`), and happy path.
- Institution and region isolation tests pass.
- Audit rows exist for record upsert, document upload/review, and snapshot generation.
- AI suggestions remain unverified until explicitly confirmed by College Admin.

---

## Definition of Done

- [ ] `0003_readiness_assessment.py` applies and rolls back cleanly.
- [ ] Institution programme mapping to APH `programme_key` works.
- [ ] Structured infrastructure record upsert works with institution-level authorization.
- [ ] Document upload and AI extraction reuse Module 1 services.
- [ ] Extracted values preserve source document and page provenance.
- [ ] AI-extracted values require College Admin verification.
- [ ] Comparison supports numeric/string rules and all four statuses.
- [ ] Snapshots preserve APH version, programme mapping, values, and results at assessment time.
- [ ] College Admin cannot access another institution's records or snapshots.
- [ ] Regional Officer sees only authorized regional snapshots.
- [ ] Audit rows exist for relevant write and assessment actions.
- [ ] Frontend entry, document review, and report pages work against the real API.
- [ ] No frontend mock data.
- [ ] Automated Gemini tests use a fake client.
- [ ] Readiness reports are advisory and are not presented as official AICTE approval.

---

## Deployment Checkpoint

Deploy backend to Render and frontend to Vercel. On live URLs, run the workflow using a seeded College Admin:

1. Open infrastructure entry and save form-based records.
2. Upload a synthetic institutional PDF.
3. Review and confirm AI-extracted suggestions.
4. Run a readiness assessment.
5. View the generated gap report.
6. Verify institution and regional access restrictions.
7. Confirm snapshots, records, document metadata, and audit rows in Neon.
8. Confirm signed document URLs work with private Cloudflare R2 storage.
9. Check Render cold-start behavior and frontend error handling.

Do not use real college personal data for the prototype.

---

## Notes for Module 3

- Module 3 consumes the verified institutional profile and readiness snapshots created here.
- An application must reference the relevant published `aph_version_id`.
- Preserve the readiness snapshot used when the application was submitted; do not silently replace it with a newer assessment.
- A readiness gap informs scrutiny but must not automatically approve, reject, or block a statutory decision.
- Programme mappings and parameter keys must remain consistent with Module 1.
