-- Seed roles reference data and optional demo admin for Oracle environments.
-- Prefer provisioning ADMIN via LDAP/AD group mapping in production.

-- Example: create application user (run as SYS)
-- CREATE TABLESPACE aop_data DATAFILE 'aop_data01.dbf' SIZE 2G AUTOEXTEND ON;
-- CREATE USER aop_app IDENTIFIED BY "CHANGE_ME" DEFAULT TABLESPACE aop_data QUOTA UNLIMITED ON aop_data;
-- GRANT CONNECT, RESOURCE TO aop_app;
-- GRANT CREATE VIEW, CREATE SEQUENCE TO aop_app;
