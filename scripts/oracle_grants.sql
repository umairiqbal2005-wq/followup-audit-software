-- =============================================================================
-- Least-privilege grants — run as AOP_OWNER after oracle_ddl.sql
-- Runtime user: AOP_APP (DML only; no DDL, no DELETE on core tables)
-- Application sets ALTER SESSION SET CURRENT_SCHEMA = AOP_OWNER on connect.
-- =============================================================================

GRANT SELECT, INSERT, UPDATE ON users TO aop_app;
GRANT SELECT, INSERT, UPDATE ON audit_reports TO aop_app;
GRANT SELECT, INSERT, UPDATE ON observations TO aop_app;
GRANT SELECT, INSERT, UPDATE ON observation_responses TO aop_app;
GRANT SELECT, INSERT ON observation_history TO aop_app;
-- Intentionally NO DELETE on core tables for the runtime user.
-- Intentionally NO UPDATE/DELETE on observation_history.

GRANT SELECT ON obs_number_seq TO aop_app;

-- Verify as AOP_OWNER:
-- SELECT table_name, privilege FROM user_tab_privs_made WHERE grantee = 'AOP_APP' ORDER BY 1,2;
