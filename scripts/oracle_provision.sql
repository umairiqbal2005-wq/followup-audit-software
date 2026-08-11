-- =============================================================================
-- AOP Oracle provisioning (run as SYSDBA / privileged DBA)
-- Target: Oracle 19c+ (CDB/PDB). Adjust paths/sizes to site standards.
-- Creates: dedicated tablespaces, hardened profile, schema owner, runtime app user
-- =============================================================================

-- Optional: switch to application PDB
-- ALTER SESSION SET CONTAINER = XEPDB1;

-- ---------------------------------------------------------------------------
-- 1) Tablespaces (data + index separation; no TEMP/UNDO changes here)
-- ---------------------------------------------------------------------------
CREATE TABLESPACE aop_data
  DATAFILE SIZE 2G AUTOEXTEND ON NEXT 256M MAXSIZE 64G
  EXTENT MANAGEMENT LOCAL AUTOALLOCATE
  SEGMENT SPACE MANAGEMENT AUTO;

CREATE TABLESPACE aop_index
  DATAFILE SIZE 1G AUTOEXTEND ON NEXT 128M MAXSIZE 32G
  EXTENT MANAGEMENT LOCAL AUTOALLOCATE
  SEGMENT SPACE MANAGEMENT AUTO;

-- ---------------------------------------------------------------------------
-- 2) Password / resource profile for application accounts
-- ---------------------------------------------------------------------------
CREATE PROFILE aop_app_profile LIMIT
  FAILED_LOGIN_ATTEMPTS 5
  PASSWORD_LOCK_TIME 1/24          -- 1 hour
  PASSWORD_LIFE_TIME 90
  PASSWORD_GRACE_TIME 7
  PASSWORD_REUSE_TIME 365
  PASSWORD_REUSE_MAX 10
  PASSWORD_VERIFY_FUNCTION ORA12C_VERIFY_FUNCTION
  IDLE_TIME 30
  CONNECT_TIME UNLIMITED
  SESSIONS_PER_USER 80
  CPU_PER_SESSION UNLIMITED
  LOGICAL_READS_PER_SESSION UNLIMITED;

-- ---------------------------------------------------------------------------
-- 3) Schema owner: owns objects, not used by application at runtime
-- ---------------------------------------------------------------------------
CREATE USER aop_owner IDENTIFIED BY "CHANGE_ME_OWNER_PWD"
  DEFAULT TABLESPACE aop_data
  TEMPORARY TABLESPACE temp
  PROFILE aop_app_profile
  ACCOUNT UNLOCK
  QUOTA UNLIMITED ON aop_data
  QUOTA UNLIMITED ON aop_index;

GRANT CREATE SESSION TO aop_owner;
GRANT CREATE TABLE, CREATE VIEW, CREATE SEQUENCE, CREATE PROCEDURE, CREATE TRIGGER TO aop_owner;
-- Explicitly NOT granted: DBA, SELECT ANY TABLE, EXP_FULL_DATABASE, etc.

-- ---------------------------------------------------------------------------
-- 4) Runtime application user: DML only via grants/synonyms (no DDL)
-- ---------------------------------------------------------------------------
CREATE USER aop_app IDENTIFIED BY "CHANGE_ME_APP_PWD"
  DEFAULT TABLESPACE aop_data
  TEMPORARY TABLESPACE temp
  PROFILE aop_app_profile
  ACCOUNT UNLOCK
  QUOTA 0 ON aop_data
  QUOTA 0 ON aop_index;

GRANT CREATE SESSION TO aop_app;
-- No CREATE TABLE / RESOURCE for runtime user.

-- ---------------------------------------------------------------------------
-- 5) Network / encryption reminders (DBA checklist; site-specific)
-- ---------------------------------------------------------------------------
-- * Prefer TCPS listener endpoints; disable cleartext 1521 if policy allows
-- * Use sqlnet.ora: SQLNET.ENCRYPTION_SERVER = REQUIRED (or TCPS-only)
-- * Restrict listener to app subnet; block direct end-user DB access
-- * Keep aop_owner password in vault; rotate independently from aop_app
-- * After DDL: run oracle_grants.sql as aop_owner
-- * Enable Unified Audit policies from oracle_hardening.sql as SYSDBA
