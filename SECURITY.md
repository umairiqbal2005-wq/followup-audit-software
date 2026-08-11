# Security Overview — Audit Observations Platform

For information security review of in-house VM deployment.

## Trust boundaries

| Zone | Components | Notes |
|------|------------|-------|
| External / corporate network | Browser clients | Prefer VPN / Zero Trust access |
| DMZ / edge | Nginx TLS termination | Only 443 exposed |
| App tier | FastAPI replicas | No direct DB exposure |
| Data tier | Oracle, Redis, LDAP | Private VLAN |

## Authentication

- Production: LDAP / Active Directory bind verification
- Local password hashes (bcrypt) for development or break-glass admin only
- API auth via JWT Bearer tokens (`HS256`); rotate `SECRET_KEY` per environment
- Role-based access control:
  - `ADMIN`, `CENTRAL_TEAM`, `PROCESS_OWNER`, `AUDITOR`, `VIEWER`
- Dev user bootstrap is disabled when `APP_ENV=production` or `LDAP_ENABLED=true`

## Authorization (workflow)

- Observations filtered for process owners (assigned only)
- Assign / verify limited to central team (and admin)
- Report upload limited to auditor / central / admin
- User administration limited to admin

## Oracle database controls

| Control | Implementation |
|---------|----------------|
| Separation of duties | `AOP_OWNER` (DDL) vs `AOP_APP` (runtime DML) |
| Least privilege | No DELETE for app user; history INSERT/SELECT only |
| Schema resolution | `CURRENT_SCHEMA=AOP_OWNER` set per connection |
| Transport | Prefer TCPS + Oracle wallet; password URL-encoded |
| Timeouts | TCP connect + `call_timeout` on DBAPI connections |
| Pool hygiene | `pool_pre_ping`, LIFO, recycle, bounded overflow |
| Immutable audit trail | Trigger blocks UPDATE/DELETE on `observation_history` |
| Closed-record integrity | Trigger prevents reopening CLOSED rows via SQL |
| Password policy | Profile: lockout, life/reuse, verify function |
| Unified Audit | Policies for privileges, app DML, logon |
| No auto-DDL in prod | `ORACLE_MANAGE_SCHEMA_EXTERNALLY=true` |
| Identifier safety | Schema/edition names validated before session SQL |

See `scripts/oracle_provision.sql`, `oracle_ddl.sql`, `oracle_grants.sql`, `oracle_hardening.sql`.

## Data classification

- Audit observations and reports are typically **confidential / internal**
- Upload content may include regulated findings — apply corporate DLP and retention
- Observation history provides non-repudiation of status transitions

## Controls

- TLS at edge (Nginx or corporate load balancer)
- Parameterized SQL via SQLAlchemy (mitigates injection)
- Upload allow-list: PDF / Excel / CSV; size capped (`MAX_UPLOAD_MB`)
- CORS restricted to configured origins
- Passwords never logged; LDAP bind failures return generic auth errors
- Horizontal scale without shared local session state

## Logging & monitoring

- Prefer centralized app logs (request id, user id, action) without PII in clear text beyond need
- Alert on repeated auth failures, privilege denials, and upload errors
- Retain observation history for audit trail requirements
- Review Unified Audit records for `AOP_APP` / `AOP_OWNER` regularly

## Recommendations for SecOps

1. Enforce LDAPS and service account rotation
2. Store `SECRET_KEY`, Oracle passwords, and wallet material in vault / HSM-backed secret store
3. Lock `AOP_OWNER` except during approved migration windows
4. Scan container images in CI before promotion
5. Periodic access review of `ADMIN` / `CENTRAL_TEAM` membership
6. Backup encryption and tested restore for Oracle + upload volume
7. Confirm `/ready` fails closed when DB grants or TCPS wallet are misconfigured
