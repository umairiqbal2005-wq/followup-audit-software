# Deployment Guide — Audit Observations Platform

## Target topology

- Nginx for TLS termination and reverse proxy
- N × FastAPI backend workers (stateless)
- Oracle Database 19c+ (primary store)
- Redis for optional session/revocation lists
- LDAP / Active Directory for authentication

Designed for in-house VM deployment with **800+ concurrent users**.

## VM sizing (starting point)

| Tier | Spec | Notes |
|------|------|-------|
| App (×2+) | 8 vCPU, 16 GB RAM | Uvicorn/Gunicorn workers; scale horizontally |
| Nginx | 4 vCPU, 8 GB RAM | Can share with LB appliance |
| Oracle | 16+ vCPU, 64+ GB RAM | Follow Oracle sizing for concurrent OLTP |
| Redis | 2 vCPU, 4 GB RAM | Session/token helpers only |

For 800 concurrent interactive users, prefer **3–4 API replicas** behind Nginx `least_conn`, each running multiple Uvicorn workers (`(2 × CPU) + 1`).

## Oracle hardening (required for production)

### Deployment order

1. `scripts/oracle_provision.sql` — SYSDBA: tablespaces, profile, `AOP_OWNER` + `AOP_APP`
2. `scripts/oracle_ddl.sql` — as `AOP_OWNER`: tables, indexes, sequences, triggers
3. `scripts/oracle_grants.sql` — as `AOP_OWNER`: least-privilege grants to `AOP_APP`
4. `scripts/oracle_hardening.sql` — SYSDBA: Unified Audit policies
5. Point the API at **`AOP_APP`** (never `AOP_OWNER`) with TCPS/wallet settings

### Least privilege model

| Account | Purpose | Privileges |
|---------|---------|------------|
| `AOP_OWNER` | Schema owner / migrations only | DDL on AOP objects; lock when idle |
| `AOP_APP` | Runtime API connections | `SELECT/INSERT/UPDATE` on tables; `INSERT` only on history; **no DELETE**, **no DDL** |

The API sets `ALTER SESSION SET CURRENT_SCHEMA = AOP_OWNER` on each connection so unqualified ORM names resolve correctly.

### Network / encryption

- Prefer **TCPS** listener (e.g. port 2484) and Oracle wallet on app hosts
- Set `SQLNET.ENCRYPTION_SERVER = REQUIRED` (or TCPS-only) on the database
- Restrict listener ACLs to the app subnet; no direct end-user DB access
- Store `ORACLE_PASSWORD` / wallet secrets in a vault; rotate `AOP_OWNER` and `AOP_APP` independently

### Application environment (Oracle)

```bash
DB_BACKEND=oracle
APP_ENV=production
ORACLE_USER=aop_app
ORACLE_PASSWORD=...                 # or wallet without password
ORACLE_DSN=dbhost.example.com:2484/AOPPDB
ORACLE_SCHEMA=AOP_OWNER
ORACLE_WALLET_LOCATION=/etc/aop/wallet
ORACLE_CONFIG_DIR=/etc/aop/wallet
ORACLE_CALL_TIMEOUT_MS=60000
ORACLE_POOL_SIZE=20
ORACLE_MAX_OVERFLOW=40
ORACLE_POOL_RECYCLE_SEC=1800
ORACLE_MANAGE_SCHEMA_EXTERNALLY=true
DISABLE_DEV_BOOTSTRAP=true
LDAP_ENABLED=true
```

### Runtime protections already in DDL / app

- Append-only `observation_history` (DB trigger blocks UPDATE/DELETE)
- Closed observations cannot be reopened via direct SQL UPDATE
- Race-safe `OBS_NUMBER_SEQ` for observation numbers
- Separate data/index tablespaces
- Password profile: failed logins, reuse, life time, `ORA12C_VERIFY_FUNCTION`
- SQLAlchemy `create_all` and local user bootstrap **disabled** in production/Oracle
- Connection pool: pre-ping, LIFO, recycle, call timeout
- `/health` and `/ready` probe database readiness

### Tuning / ops

- Monitor `V$SESSION`, pool wait, and p95 API latency during review peaks
- RMAN + archive log shipping; encrypt backups
- Keep upload volume RPO aligned with DB RPO
- After schema changes: migrate as `AOP_OWNER`, re-run grants if new objects appear

## LDAP / Active Directory

1. Set `LDAP_ENABLED=true` and bind credentials.
2. Map AD groups to AOP roles via admin UI after first login (users auto-provision as `VIEWER`).
3. Prefer LDAPS (`LDAP_USE_SSL=true`) in production.

## Application rollout

```bash
# Build and start (dev-friendly compose; SQLite)
docker compose up -d --build

# Production overlay (Oracle + LDAP + Redis)
export SECRET_KEY=... ORACLE_DSN=... ORACLE_USER=aop_app ORACLE_PASSWORD=... LDAP_URL=...
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Health: `GET /health` · Readiness: `GET /ready`

## Scaling checklist

- Keep backends **stateless** (JWT auth; files on shared NFS/object store if multi-node uploads)
- Put uploads on shared volume when running >1 backend
- Size `ORACLE_POOL_SIZE` × replicas below Oracle `SESSIONS` / profile `SESSIONS_PER_USER`
- Enable Redis when using token denylist helpers
- Rate-limit login at Nginx if exposed beyond corporate VPN

## Backups

- Oracle: daily RMAN + archive log shipping
- Uploaded files: filesystem/NFS snapshot aligned with DB RPO
- Redis: optional AOF; non-authoritative
