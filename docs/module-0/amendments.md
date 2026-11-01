# Module 0 Amendments (final decisions)

**Precedence:** this file overrides tasks.md, which overrides design.md, which overrides requirements.md. Where a document contradicts a later one, follow the later one.

## A. Amendments to the requirements

1. Add CORS: allowed origins read from the `CORS_ORIGINS` environment variable.
2. Database connection: SSL required in `DATABASE_URL`, `pool_pre_ping` enabled, and a `GET /health` endpoint returning 200.
3. Seed data: three `college_admin` users, one per institution. Add a `region` field to institutions and users (a regional officer is scoped by region). The seed creates 8 users, not 6.
4. Append-only is enforced at database level for `application_history` and `audit_log` (migration with triggers). Failed logins are recorded in the audit log.
5. Tests run against a real Postgres (separate Neon branch or local Docker). Not SQLite, not mocks.
6. Keep tables for later modules minimal (core columns and relationships only). They will be extended through migrations.

## B. Amendments to the design

1. `record_audit` commits independently (its own session), so audit rows persist when the request fails with 401 or 403. Test fixtures use a savepoint (nested transaction) pattern so endpoints that commit do not break test isolation.
2. Define a `set_updated_at` trigger for all tables except the append-only ones. Add `BEFORE TRUNCATE` protection on `audit_log` and `application_history`.
3. Add `users.institution_id` (FK to institutions, nullable). Drop `institutions.admin_user_id`.
4. Use `HTTPBearer`, not `OAuth2PasswordBearer`, so Swagger's Authorize accepts a pasted token. `require_roles` reloads the user from the database on each request and rejects `is_active = false`.
5. Split health endpoints: `GET /health` (no database call) and `GET /health/db` (`SELECT 1`).
6. Add frontend `vercel.json` with an SPA rewrite. Add handling so `CORS_ORIGINS` accepts comma-separated values.
7. Corrections: 17 tables (not 18), 8 seed users, and `roles` and `workflow_stages` are seeded only in the migration, not in `seed.py`.

## C. Amendments to the tasks

1. `config.py`: store `CORS_ORIGINS` as a plain `str` and expose a `cors_origins_list` property that splits on commas. Do not use `list[str]` with a validator (pydantic-settings tries to parse it as JSON).
2. Migration order: `roles`, `workflow_stages`, `institutions`, `users`, then the rest. Use `server_default=gen_random_uuid()` on all `id` columns. Add a UNIQUE constraint on `institutions.name` (the seed relies on it).
3. Test design:
   - Create the 8 role users plus one permanently inactive user once per session as committed rows.
   - Audit assertions must filter by a unique email in `detail`, never count all rows.
   - At session start run `alembic downgrade base` then `upgrade head` on `TEST_DATABASE_URL`.
   - Override `SessionLocal` so `record_audit` uses the test database.
4. Add `GET /admin/ping`, protected by `require_roles(["main_admin"])`, for RBAC tests.
5. Add `email-validator` to `requirements.txt`. Remove `pytest-asyncio`.
6. Do not pin versions from memory. Use `npm create vite@latest` and `npx shadcn@latest init` and rely on the lockfile. For Python, pip install then `pip freeze`. Add Shadcn `input`, `label` and `alert` components.
7. `require_roles` must be a synchronous `def`. Return 401 on an invalid UUID in the token.
8. CORS `allow_credentials=False`. Pass the client IP into `record_audit` from `/auth/login`.
9. Deployment doc: free Render has no shell, so `seed.py` runs locally against the Neon `DATABASE_URL`. Add deploy checkpoints after Task 10 (Render + Neon) and after Task 16 (Vercel).

## D. Known fixes discovered during implementation

1. TypeScript `baseUrl` is removed in newer TypeScript. Remove `"baseUrl"` from `tsconfig.app.json` and `tsconfig.json`; keep `"paths": { "@/*": ["./src/*"] }`. Keep the `@` alias in `vite.config.ts` and install `@types/node`.
2. Frontend rule: no hard-coded colors, fonts or spacing in components. Use theme tokens (CSS variables) only, so a government-style theme (UX4G / GIGW) can be applied after Module 0.
