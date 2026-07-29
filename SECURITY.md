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

## Authorization (workflow)

- Observations filtered for process owners (assigned only)
- Assign / verify limited to central team (and admin)
- Report upload limited to auditor / central / admin
- User administration limited to admin

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
- Oracle least-privilege application schema (no DBA grants to app user)
- Horizontal scale without shared local session state

## Logging & monitoring

- Prefer centralized app logs (request id, user id, action) without PII in clear text beyond need
- Alert on repeated auth failures, privilege denials, and upload errors
- Retain observation history for audit trail requirements

## Recommendations for SecOps

1. Enforce LDAPS and service account rotation
2. Store `SECRET_KEY` and DB credentials in vault / HSM-backed secret store
3. Scan container images in CI before promotion
4. Periodic access review of `ADMIN` / `CENTRAL_TEAM` membership
5. Backup encryption and tested restore for Oracle + upload volume
