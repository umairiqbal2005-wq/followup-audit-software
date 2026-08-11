# Audit Observations Platform (AOP)

Enterprise application for tracking audit observations from report upload through central team review to process owner closure. Designed for in-house VM deployment with 800+ concurrent users.

## Architecture

```
                    ┌─────────────┐
                    │   Nginx     │  TLS termination, load balancing
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐           ┌──────▼──────┐
       │  Frontend   │           │   Backend   │  FastAPI (stateless, horizontal scale)
       │  React SPA  │           │   API x N   │
       └─────────────┘           └──────┬──────┘
                                        │
                         ┌──────────────┼──────────────┐
                         │              │              │
                  ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
                  │   Oracle    │ │   Redis   │ │    LDAP     │
                  │  Database   │ │  Sessions │ │  Active Dir │
                  └─────────────┘ └───────────┘ └─────────────┘
```

## Workflow

1. **Upload** — Audit report uploaded (PDF/Excel); observations entered against the report.
2. **Central Review** — Central team reviews, categorizes, and assigns to process owners.
3. **Owner Response** — Process owners respond: resolved, need more time, or committed timeline.
4. **Verification** — Central team verifies closure and closes the observation.

## Roles

| Role | Capabilities |
|------|-------------|
| `ADMIN` | User management, system configuration |
| `CENTRAL_TEAM` | Review observations, assign owners, verify closure |
| `PROCESS_OWNER` | Respond to assigned observations |
| `AUDITOR` | Create reports/observations, read status |
| `VIEWER` | Dashboard and summary reports only |

Region windows: `NORTH`, `SOUTH`, `CENTRAL`  
Segments: `BRANCH_AUDIT`, `SHARIAH`, `MANAGEMENT`, `OTHER`

Admins assign both functional role and region/segment access on the Users page. Non-admin users only see reports and observations inside their assigned windows.

## Quick Start (Development)

### Prerequisites

- Python 3.11+
- Node.js 20+
- Oracle Database 19c+ for production (SQLite included for local API development)
- Redis 7+ (optional in development)
- LDAP/AD (optional; local users seeded when disabled)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Edit Oracle & LDAP settings for prod
uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

Seeded local users (LDAP disabled):

| Username | Password | Role |
|----------|----------|------|
| `admin` | `demo123` | ADMIN |
| `umair` | `demo123` | ADMIN (owner — manage roles & regions) |
| `central1` | `demo123` | CENTRAL_TEAM |
| `owner1` | `demo123` | PROCESS_OWNER |
| `auditor1` | `demo123` | AUDITOR |
| `viewer1` | `demo123` | VIEWER |
| `khurrum` | `demo123` | VIEWER (North region only, all segments) |
| `north_auditor` | `demo123` | AUDITOR (North) |
| `south_viewer` | `demo123` | VIEWER (South) |

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Full stack (Docker)

```bash
docker compose up -d --build
```

Access: `http://localhost:3000` (frontend) · `http://localhost:8000/docs` (API docs)

### Tests

```bash
cd backend
pytest -q
```

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for VM sizing, Oracle tuning, LDAP integration, and scaling to 800+ users.

## Security Review

See [SECURITY.md](SECURITY.md) for architecture, data flows, authentication, and controls for your information security team.

## Oracle production hardening

Apply scripts in order (see [DEPLOYMENT.md](DEPLOYMENT.md)):

1. `scripts/oracle_provision.sql` (SYSDBA) — tablespaces, profile, `AOP_OWNER` / `AOP_APP`
2. `scripts/oracle_ddl.sql` (`AOP_OWNER`) — schema, indexes, immutable history triggers
3. `scripts/oracle_grants.sql` (`AOP_OWNER`) — least-privilege grants to runtime user
4. `scripts/oracle_hardening.sql` (SYSDBA) — Unified Audit policies

Runtime API must connect as **`aop_app`** with `ORACLE_SCHEMA=AOP_OWNER` (and preferably TCPS/wallet).

## Source Code Layout

```
backend/app/          # Python FastAPI application
frontend/src/         # React TypeScript SPA
scripts/              # Oracle provision, DDL, grants, hardening
nginx/                # Reverse proxy configuration
docker-compose*.yml   # Container orchestration
```

## License

Proprietary — Internal use only. All rights reserved by deploying organization.
