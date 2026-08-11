-- =============================================================================
-- Oracle hardening controls for AOP — run as SYSDBA in the application PDB
-- Complements provision/DDL/grants. Adjust policy names to site standards.
-- =============================================================================

-- ALTER SESSION SET CONTAINER = XEPDB1;

-- ---------------------------------------------------------------------------
-- Unified Audit: capture privileged and application-sensitive activity
-- ---------------------------------------------------------------------------
-- Verify Unified Auditing:
-- SELECT VALUE FROM V$OPTION WHERE PARAMETER = 'Unified Auditing';

BEGIN
  EXECUTE IMMEDIATE 'CREATE AUDIT POLICY aop_privilege_pol PRIVILEGES CREATE ANY TABLE, ALTER ANY TABLE, DROP ANY TABLE, SELECT ANY TABLE, GRANT ANY OBJECT PRIVILEGE, GRANT ANY PRIVILEGE';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -46358 THEN RAISE; END IF; -- policy exists
END;
/

AUDIT POLICY aop_privilege_pol;

BEGIN
  EXECUTE IMMEDIATE q'[
    CREATE AUDIT POLICY aop_app_dml_pol
      ACTIONS ALL ON aop_owner.users,
              ALL ON aop_owner.observations,
              ALL ON aop_owner.observation_history,
              ALL ON aop_owner.audit_reports
  ]';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -46358 THEN RAISE; END IF;
END;
/

AUDIT POLICY aop_app_dml_pol BY aop_app;

BEGIN
  EXECUTE IMMEDIATE 'CREATE AUDIT POLICY aop_logon_pol ACTIONS LOGON, LOGOFF';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLCODE != -46358 THEN RAISE; END IF;
END;
/

AUDIT POLICY aop_logon_pol BY aop_app, aop_owner;

-- ---------------------------------------------------------------------------
-- Deny dangerous public privileges commonly left enabled (review first)
-- ---------------------------------------------------------------------------
-- REVOKE EXECUTE ON UTL_FILE FROM PUBLIC;
-- REVOKE EXECUTE ON UTL_HTTP FROM PUBLIC;
-- REVOKE EXECUTE ON UTL_TCP FROM PUBLIC;
-- REVOKE EXECUTE ON UTL_SMTP FROM PUBLIC;

-- ---------------------------------------------------------------------------
-- Network / encryption checklist (sqlnet.ora / listener.ora — DBA)
-- ---------------------------------------------------------------------------
-- sqlnet.ora:
--   SQLNET.ENCRYPTION_SERVER = REQUIRED
--   SQLNET.ENCRYPTION_TYPES_SERVER = (AES256)
--   SQLNET.CRYPTO_CHECKSUM_SERVER = REQUIRED
--   SQLNET.CRYPTO_CHECKSUM_TYPES_SERVER = (SHA256)
--   SQLNET.EXPIRE_TIME = 10
-- Prefer TCPS wallet connectivity from the app tier; restrict listener hosts.
-- Keep AOP_OWNER locked except during schema migrations.

-- ---------------------------------------------------------------------------
-- Operational verification
-- ---------------------------------------------------------------------------
-- SELECT grantee, privilege, table_name FROM dba_tab_privs WHERE owner = 'AOP_OWNER' ORDER BY 1,3,2;
-- SELECT * FROM audit_unified_enabled_policies WHERE policy_name LIKE 'AOP_%';
-- SELECT table_name FROM dba_tables WHERE owner = 'AOP_APP';  -- expect zero rows
