"""Oracle connection helpers: TCPS/wallet, pool settings, session hardening."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from app.core.config import Settings


def is_oracle(settings: Settings) -> bool:
    return settings.db_backend.lower() == "oracle"


def build_oracle_database_url(settings: Settings) -> str:
    """Build a SQLAlchemy URL. Password is URL-encoded; wallet mode may omit password."""
    user = quote_plus(settings.oracle_user)
    dsn = settings.oracle_dsn.strip()
    if settings.oracle_wallet_location and not settings.oracle_password:
        # External / wallet auth: user@dsn without password component
        return f"oracle+oracledb://{user}@{dsn}"
    password = quote_plus(settings.oracle_password)
    return f"oracle+oracledb://{user}:{password}@{dsn}"


def build_oracle_connect_args(settings: Settings) -> dict[str, Any]:
    """python-oracledb connect kwargs for TCPS, wallets, and call timeouts."""
    args: dict[str, Any] = {}
    if settings.oracle_call_timeout_ms > 0:
        args["tcp_connect_timeout"] = max(1, settings.oracle_tcp_connect_timeout_sec)
        # call_timeout is milliseconds in python-oracledb
        args["call_timeout"] = settings.oracle_call_timeout_ms
    if settings.oracle_wallet_location:
        args["wallet_location"] = settings.oracle_wallet_location
        args["config_dir"] = settings.oracle_config_dir or settings.oracle_wallet_location
        if settings.oracle_wallet_password:
            args["wallet_password"] = settings.oracle_wallet_password
    elif settings.oracle_config_dir:
        args["config_dir"] = settings.oracle_config_dir
    if settings.oracle_disable_oob:
        args["disable_oob"] = True
    return args


def build_oracle_engine_kwargs(settings: Settings) -> dict[str, Any]:
    return {
        "pool_pre_ping": True,
        "pool_size": settings.oracle_pool_size,
        "max_overflow": settings.oracle_max_overflow,
        "pool_recycle": settings.oracle_pool_recycle_sec,
        "pool_timeout": settings.oracle_pool_timeout_sec,
        "pool_use_lifo": True,
        "connect_args": build_oracle_connect_args(settings),
    }


def session_harden_sql(settings: Settings) -> list[str]:
    """
    Statements executed on every new DBAPI connection.
    CURRENT_SCHEMA lets AOP_APP use unqualified table names owned by AOP_OWNER.
    """
    schema = validate_oracle_identifier(settings.oracle_schema)
    stmts = [
        f"ALTER SESSION SET CURRENT_SCHEMA = {schema}",
        "ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD\"T\"HH24:MI:SS'",
        "ALTER SESSION SET NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD\"T\"HH24:MI:SS.FF3'",
        "ALTER SESSION SET TIME_ZONE = 'UTC'",
    ]
    if settings.oracle_edition:
        edition = validate_oracle_identifier(settings.oracle_edition)
        stmts.append(f"ALTER SESSION SET EDITION = {edition}")
    return stmts


def validate_oracle_identifier(name: str) -> str:
    """Allow only simple unquoted Oracle identifiers (defense-in-depth for session SQL)."""
    cleaned = name.strip().upper()
    if not cleaned or not cleaned.replace("_", "").isalnum() or cleaned[0].isdigit():
        raise ValueError(f"Invalid Oracle identifier: {name!r}")
    return cleaned
