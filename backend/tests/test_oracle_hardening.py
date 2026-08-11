import os

os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("SQLITE_PATH", "./test_aop.db")

import pytest

from app.core.config import Settings, get_settings
from app.core.oracle import (
    build_oracle_connect_args,
    build_oracle_database_url,
    build_oracle_engine_kwargs,
    session_harden_sql,
    validate_oracle_identifier,
)


def test_validate_oracle_identifier_accepts_simple_names():
    assert validate_oracle_identifier("aop_owner") == "AOP_OWNER"
    assert validate_oracle_identifier("OBS_NUMBER_SEQ") == "OBS_NUMBER_SEQ"


@pytest.mark.parametrize("bad", ["", "aop-owner", "AOP OWNER", "1OWNER", "AOP;DROP"])
def test_validate_oracle_identifier_rejects_unsafe(bad):
    with pytest.raises(ValueError):
        validate_oracle_identifier(bad)


def test_oracle_url_encodes_special_password():
    settings = Settings(
        db_backend="oracle",
        oracle_user="aop_app",
        oracle_password="p@ss/w:rd",
        oracle_dsn="db.example.com:2484/AOPPDB",
    )
    url = build_oracle_database_url(settings)
    assert url.startswith("oracle+oracledb://aop_app:")
    assert "p@ss" not in url  # must be encoded
    assert "p%40ss%2Fw%3Ard" in url
    assert url.endswith("@db.example.com:2484/AOPPDB")


def test_oracle_wallet_url_omits_password_when_empty():
    settings = Settings(
        db_backend="oracle",
        oracle_user="aop_app",
        oracle_password="",
        oracle_dsn="aop_tcps",
        oracle_wallet_location="/etc/aop/wallet",
    )
    assert build_oracle_database_url(settings) == "oracle+oracledb://aop_app@aop_tcps"


def test_connect_args_include_wallet_and_timeouts():
    settings = Settings(
        db_backend="oracle",
        oracle_wallet_location="/etc/aop/wallet",
        oracle_wallet_password="wallet-secret",
        oracle_call_timeout_ms=45000,
        oracle_tcp_connect_timeout_sec=8,
    )
    args = build_oracle_connect_args(settings)
    assert args["wallet_location"] == "/etc/aop/wallet"
    assert args["config_dir"] == "/etc/aop/wallet"
    assert args["wallet_password"] == "wallet-secret"
    assert args["call_timeout"] == 45000
    assert args["tcp_connect_timeout"] == 8


def test_session_harden_sets_current_schema_and_utc():
    settings = Settings(oracle_schema="aop_owner")
    stmts = session_harden_sql(settings)
    assert stmts[0] == "ALTER SESSION SET CURRENT_SCHEMA = AOP_OWNER"
    assert any("TIME_ZONE = 'UTC'" in s for s in stmts)


def test_engine_kwargs_use_lifo_pool():
    settings = Settings(oracle_pool_size=15, oracle_max_overflow=25, oracle_pool_recycle_sec=900)
    kwargs = build_oracle_engine_kwargs(settings)
    assert kwargs["pool_size"] == 15
    assert kwargs["max_overflow"] == 25
    assert kwargs["pool_recycle"] == 900
    assert kwargs["pool_use_lifo"] is True
    assert kwargs["pool_pre_ping"] is True


def test_production_oracle_skips_create_all_and_bootstrap():
    settings = Settings(
        app_env="production",
        db_backend="oracle",
        oracle_manage_schema_externally=True,
        ldap_enabled=True,
    )
    assert settings.should_create_schema is False
    assert settings.should_bootstrap_dev_users is False


def test_settings_database_url_property_uses_oracle_builder(monkeypatch):
    monkeypatch.setenv("DB_BACKEND", "oracle")
    monkeypatch.setenv("ORACLE_USER", "aop_app")
    monkeypatch.setenv("ORACLE_PASSWORD", "x")
    monkeypatch.setenv("ORACLE_DSN", "host:1521/XEPDB1")
    get_settings.cache_clear()
    try:
        s = get_settings()
        assert s.database_url.startswith("oracle+oracledb://aop_app:")
    finally:
        get_settings.cache_clear()
