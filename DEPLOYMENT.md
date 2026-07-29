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

## Oracle

1. Create tablespace and application user (see `scripts/oracle_seed.sql` comments).
2. Apply `scripts/oracle_ddl.sql`.
3. Set backend env:
   - `DB_BACKEND=oracle`
   - `ORACLE_USER` / `ORACLE_PASSWORD` / `ORACLE_DSN`
4. Tune:
   - Connection pool: `pool_size=20`, `max_overflow=40` (already configured)
   - Indexes on `observations.status`, `owner_id`, `due_date` (included in DDL)
   - Archive logs and RMAN backups per corporate standard

## LDAP / Active Directory

1. Set `LDAP_ENABLED=true` and bind credentials.
2. Map AD groups to AOP roles via admin UI after first login (users auto-provision as `VIEWER`).
3. Prefer LDAPS (`LDAP_USE_SSL=true`) in production.

## Application rollout

```bash
# Build and start (dev-friendly compose)
docker compose up -d --build

# Production overlay
export SECRET_KEY=... ORACLE_DSN=... LDAP_URL=...
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Health check: `GET /health`

## Scaling checklist

- Keep backends **stateless** (JWT auth; files on shared NFS/object store if multi-node uploads)
- Put uploads on shared volume when running >1 backend
- Enable Redis when using token denylist / sticky session helpers
- Monitor p95 API latency and Oracle sessions during peak review cycles
- Rate-limit login at Nginx if exposed beyond corporate VPN

## Backups

- Oracle: daily RMAN + archive log shipping
- Uploaded files: filesystem/NFS snapshot aligned with DB RPO
- Redis: optional AOF; non-authoritative
