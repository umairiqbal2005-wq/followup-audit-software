# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
Audit Observations Platform (AOP): a FastAPI backend (`backend/`) + React/Vite SPA (`frontend/`).
Standard commands and seeded dev users live in `README.md` (Quick Start section) — use it as the
source of truth; only the non-obvious caveats below are worth remembering.

### Services and how to run them (local dev)
- Backend (FastAPI): from `backend/`, run `.venv/bin/uvicorn app.main:app --reload --port 8000`.
  API docs at `http://localhost:8000/docs`, health at `http://localhost:8000/health`.
- Frontend (Vite): from `frontend/`, run `npm run dev` (serves on port `3000`). The Vite dev server
  proxies `/api` and `/health` to `http://localhost:8000`, so the backend MUST be running too or all
  API calls 404/500.

### Non-obvious caveats
- Python deps are installed into a virtualenv at `backend/.venv` (created by the update script).
  Always invoke backend tooling via `backend/.venv/bin/...` (e.g. `pytest`, `uvicorn`); there is no
  global install.
- OS prerequisites `python3-venv` and `python3-pip` must be present for the update script to build the
  venv. They are installed at the OS level (apt), not by the update script.
- No `.env` is required for local dev. `backend/app/core/config.py` defaults to `DB_BACKEND=sqlite`
  with Redis/LDAP disabled, so the backend runs with zero external services.
- On startup the backend auto-creates the SQLite schema and seeds dev users (see the users table in
  `README.md`). The SQLite file defaults to `backend/aop.db`; delete it to reset local data.
- Oracle, Redis, and LDAP are production-only. Do NOT stand them up for local dev/testing — the
  `docker-compose.yml` `full`/`oracle` profiles and `oracledb`/`ldap3` deps exist only for prod parity.
- Lint = type-check only: `npm run lint` (and `npm run build`) run `tsc --noEmit`; there is no ESLint.
- Backend tests: from `backend/`, run `.venv/bin/pytest -q` (uses a throwaway SQLite db).
