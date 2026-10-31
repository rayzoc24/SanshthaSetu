# SanshthaSetu: Project Context (SIH 2026, Team Port2Code)

Read this file fully before every task. It is the single source of truth for the project. If a request conflicts with this file, say so before coding.

## 1. What we are building

**Problem statement:** SIH26262, Integrated AICTE Approval Workflow Automation, Compliance Monitoring and Alert Management System.

A web platform with three portals (College, AICTE Admin, EVC) that:
1. Turns the published AICTE Approval Process Handbook (APH) into structured, admin-verified rules.
2. Lets colleges check infrastructure readiness against those rules before applying.
3. Routes applications through approval stages defined by those rules.
4. Supports EVC inspections with digital checklists and reports.
5. Monitors post-approval compliance (undertakings, lease validity, document expiry) with alerts and escalation.

**Core principle:** AI assists, humans decide. AI never approves or rejects anything. Every statutory action is a human action by an authenticated user and is written to the audit log.

This is a **prototype** for a hackathon demo. It uses synthetic data only. It is not integrated with real AICTE systems.

## 2. The one demo story (everything we build must serve this)

1. Main Admin uploads an APH PDF. The system extracts requirements. Admin reviews, edits, and publishes a version.
2. College Admin enters infrastructure data and sees a readiness gap report (met / partial / missing).
3. College submits an application.
4. Officer scrutinizes it, raises a deficiency. College resubmits.
5. Application moves to EVC. EVC member completes a digital checklist and submits a report.
6. Competent Authority records the final decision (human action).
7. After approval, compliance items are created. A deadline approaches or passes, and an alert and escalation fire.
8. Dashboard shows stage-wise pendency, average time per stage, and the slowest stage.

## 3. Roles (RBAC)

| Role | Portal | Can do |
|---|---|---|
| College Admin | College | Manage profile, enter infrastructure, view readiness report, submit and track applications, respond to deficiencies, upload compliance documents |
| Main Admin | Admin | Upload and publish APH versions, manage users and roles, view all dashboards |
| Regional Officer | Admin (restricted) | Scrutinize applications in own region, raise deficiencies, assign EVC |
| Bureau Officer | Admin (restricted) | View bureau-level workload and processing statistics |
| EVC Member | EVC | View assigned colleges, fill inspection checklist, submit report |
| Competent Authority | Admin (restricted) | Record final approval or rejection |

Every endpoint must enforce role checks on the server. Never rely on the UI to hide actions.

## 4. Scope

**In scope (P0):** auth and RBAC, APH upload / extract / verify / publish, college registration and readiness, dynamic workflow, EVC checklist and report, compliance tracking, alerts, audit log, basic dashboard.

**Out of scope for the prototype (roadmap only; do not build unless asked):**
- Scanned-document OCR with PaddleOCR
- ML delay prediction (we show stage-time statistics only)
- Workload recommendation engine
- PDF and Excel export
- SMS, AI chat assistant, digital signature integration
- Real AICTE or government system integration

## 5. Tech stack (fixed; do not add libraries without asking)

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Shadcn UI, React Router, Zustand, TanStack Query, Axios, Recharts
- **Backend:** Python, FastAPI, SQLAlchemy, Alembic, Pydantic, PyJWT, argon2-cffi, APScheduler
- **Database:** PostgreSQL (Neon free tier)
- **File storage:** Cloudflare R2 (S3-compatible, signed URLs)
- **AI:** Gemini API (free key from Google AI Studio, Flash model, structured JSON output), PyMuPDF for PDF text
- **Email:** SMTP (Gmail app password)
- **Hosting:** Vercel (frontend), Render free web service (backend)
- **CI:** GitHub, GitHub Actions (also used as the scheduled trigger for compliance checks)

## 6. Free-tier constraints (design around these)

- The Render free service sleeps after idle time. No always-on workers: use APScheduler in the API process plus an external scheduled ping to `/internal/run-checks` (protected by a secret key).
- Neon free database is 0.5 GB. Keep seed data small.
- Gemini free tier has rate limits and the data may be used by Google. Send only the public APH text and synthetic documents. Cache and store every extraction result so it is never re-run unnecessarily.
- No Celery or separate Redis worker in the prototype.

## 7. Core data model (entities)

users, roles, institutions, programmes, aph_versions, aph_rules (programme, category, parameter, operator, value, unit, source_page), infrastructure_records, applications, workflow_stages, application_history, documents, evc_assignments, inspection_checklists, inspection_reports, compliance_items, alerts, audit_log.

Rules:
- Every table has `id`, `created_at`, `updated_at`.
- Applications and rules reference an `aph_version_id`.
- `application_history` and `audit_log` are append-only. Never update or delete rows.
- Use migrations (Alembic) for every schema change. Do not edit tables by hand.

## 8. Workflow

Stages: Submission, Scrutiny, Re-scrutiny (if deficiency), EVC Review, SAC/SHC Review, Final Decision.

- Stages and allowed transitions are defined in a config (JSON or table), not hard-coded in UI or endpoints.
- One function, `move_application(app_id, action, user)`, performs every transition. It checks the user's role, validates the transition, writes history and the audit log, and triggers notifications.
- Approval and rejection are only possible through a human user with the Competent Authority role.

## 9. AI usage rules

- Extraction output must validate against a Pydantic schema. On validation failure, log it and surface it to the admin; never silently accept.
- Extracted rules stay in `draft` until a Main Admin reviews and publishes.
- Missing-document flags and readiness gaps are recommendations shown to humans. They never block or decide anything on their own.
- Label every AI-generated value in the UI as AI-suggested.

## 10. Coding rules for the AI assistant

1. Work on one task at a time. Do not build features that were not requested.
2. Backend first: make the endpoint work and testable in Swagger (`/docs`), then build the screen that calls it.
3. No mock data in the frontend. Every screen calls the real API.
4. Do not rename or delete existing files, tables or endpoints without asking.
5. Do not refactor code unrelated to the current task.
6. Do not add a library without asking. State why it is needed.
7. Secrets only in `.env` (gitignored). Never hard-code keys. Provide `.env.example`.
8. Validate all input with Pydantic. Return consistent error shapes.
9. Write unit tests for pure logic (readiness comparison, workflow transitions, permission checks).
10. After each task, list files changed, assumptions made, and how to test.

## 11. Repository layout

```
/backend   FastAPI app (app/, models/, schemas/, routers/, services/, tests/), alembic/
/frontend  React app (src/pages, components, api, store)
/docs      this file, notes
seed.py    creates demo data
```

## 12. Definition of done (per feature)

- Works end to end against the real database
- Permission checks tested with the wrong role
- Action recorded in the audit log where relevant
- Deployed and working on the hosted URLs
- Committed with a clear message

## 13. Current status

(Update at the end of every working session: what works, what is broken, what is next.)

- Done: nothing yet
- In progress: project setup
- Next: foundation (repo, auth, RBAC, database schema)
