-- Seed notes for Oracle environments.
-- Prefer provisioning ADMIN via LDAP/AD group mapping in production.
-- Do not embed real passwords in this file.

-- Deployment order:
--   1) scripts/oracle_provision.sql   (SYSDBA)
--   2) scripts/oracle_ddl.sql         (AOP_OWNER)
--   3) scripts/oracle_grants.sql      (AOP_OWNER)
--   4) scripts/oracle_hardening.sql   (SYSDBA)
--   5) Point API at AOP_APP with TCPS/wallet settings

-- Optional break-glass local admin (only if LDAP unavailable). Prefer app bootstrap
-- with LDAP_ENABLED=false in a controlled window, then disable local passwords.
