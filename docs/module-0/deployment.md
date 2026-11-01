# SanshthaSetu — Deployment Guide (Module 0 / Task 17)

This document details the exact deployment architecture and step-by-step procedures for hosting SanshthaSetu on **Neon** (Database & Object Storage), **Render** (Backend FastAPI), and **Vercel** (Frontend React).

---

## Architecture Overview

- **Database & Storage**: [Neon](https://neon.tech)
  - **Database**: PostgreSQL (Lakebase architecture with autoscaling and branching).
  - **Object Storage**: S3-compatible bucket (`assets`) attached to the production branch.
- **Backend**: [Render](https://render.com)
  - Python Web Service running FastAPI via Uvicorn.
  - Render free tier spins down after inactivity; health check points to `/health`.
- **Frontend**: [Vercel](https://vercel.com)
  - React + Vite SPA with `vercel.json` rewrite routing.

---

## 1. Database & Storage Deployment (Neon)

Neon is managed via the Neon CLI and infrastructure config (`neon.ts`):

1. **Initialize and deploy Neon services**:
   ```bash
   neon init -y --org-id <your-org-id> --project-id <your-project-id> --branch production --services postgres --services object-storage
   neon deploy
   ```
2. **Migrations & Seed (Executed locally against Neon)**:
   *Note: Free-tier Render has no SSH shell, so schema migrations and seed scripts must run against the Neon connection string from a deployment machine or CI.*
   ```bash
   cd backend
   python -m alembic upgrade head
   python seed.py
   ```

---

## 2. Backend Deployment (Render)

1. Create a **Web Service** on Render connected to the GitHub repository.
2. Configure settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
3. Set **Environment Variables** in Render Dashboard:
   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Neon pooled PostgreSQL URL (`postgresql+psycopg2://...`) |
   | `JWT_SECRET` | 32+ character random secret |
   | `JWT_EXPIRE_HOURS` | `24` |
   | `CORS_ORIGINS` | `https://<your-app>.vercel.app,http://localhost:5173` |
   | `ENVIRONMENT` | `production` |
   | `AWS_ACCESS_KEY_ID` | Neon Storage Access Key |
   | `AWS_SECRET_ACCESS_KEY` | Neon Storage Secret Key |
   | `AWS_ENDPOINT_URL_S3` | Neon S3 endpoint URL |
   | `AWS_REGION` | `ap-southeast-1` (or your Neon region) |
   | `NEON_STORAGE_BUCKET` | `assets` |

---

## 3. Frontend Deployment (Vercel)

1. Import the GitHub repository into Vercel.
2. Configure Project:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Environment Variables:
   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://<your-render-service>.onrender.com` |
4. The repo includes `frontend/vercel.json` which automatically provides SPA rewrites:
   ```json
   {
     "rewrites": [
       { "source": "/(.*)", "destination": "/index.html" }
     ]
   }
   ```

---

## 4. Verification Checkpoint

1. **Backend Health**: `GET https://<backend>/health` returns `{"status": "ok"}` (200).
2. **Database Connectivity**: `GET https://<backend>/health/db` returns `{"status": "ok", "database": "ok"}` (200).
3. **Login Smoke Test**: Visit `https://<frontend>/login`, sign in with `main_admin@example.com` / `Demo@1234`. Successful redirect to `/admin` proves end-to-end token issuance, CORS headers, and DB authentication.
