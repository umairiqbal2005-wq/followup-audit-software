from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Audit Observations Platform"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-to-a-long-random-secret-key"
    access_token_expire_minutes: int = 480
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    db_backend: str = "sqlite"  # oracle | sqlite
    oracle_user: str = "aop_app"
    oracle_password: str = "aop_password"
    oracle_dsn: str = "localhost:1521/XEPDB1"
    # Object-owning schema; runtime user should be aop_app with CURRENT_SCHEMA set here
    oracle_schema: str = "AOP_OWNER"
    oracle_edition: str = ""
    # TCPS / Secure External Password Store / mTLS wallet
    oracle_wallet_location: str = ""
    oracle_wallet_password: str = ""
    oracle_config_dir: str = ""
    oracle_tcp_connect_timeout_sec: int = 10
    oracle_call_timeout_ms: int = 60_000
    oracle_pool_size: int = 20
    oracle_max_overflow: int = 40
    oracle_pool_recycle_sec: int = 1800
    oracle_pool_timeout_sec: int = 30
    oracle_disable_oob: bool = False
    # When true (default for oracle/production), skip SQLAlchemy create_all
    oracle_manage_schema_externally: bool = True
    sqlite_path: str = "./aop.db"

    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False

    ldap_enabled: bool = False
    ldap_url: str = "ldap://localhost:389"
    ldap_base_dn: str = "dc=example,dc=com"
    ldap_bind_dn: str = "cn=admin,dc=example,dc=com"
    ldap_bind_password: str = "admin"
    ldap_user_search_filter: str = "(sAMAccountName={username})"
    ldap_use_ssl: bool = False

    upload_dir: str = "./uploads"
    max_upload_mb: int = 25

    # Health endpoint may optionally ping DB
    health_check_db: bool = True

    dev_admin_username: str = "admin"
    dev_admin_password: str = "Admin@123"
    dev_admin_email: str = "admin@example.com"
    # Never auto-seed local users when true (production)
    disable_dev_bootstrap: bool = Field(default=False)

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def database_url(self) -> str:
        if self.db_backend.lower() == "oracle":
            from app.core.oracle import build_oracle_database_url

            return build_oracle_database_url(self)
        return f"sqlite:///{self.sqlite_path}"

    @property
    def should_create_schema(self) -> bool:
        """SQLAlchemy create_all is for sqlite/dev only. Oracle schema is DDL-managed."""
        if self.db_backend.lower() == "oracle":
            return not self.oracle_manage_schema_externally
        return True

    @property
    def should_bootstrap_dev_users(self) -> bool:
        if self.disable_dev_bootstrap or self.is_production or self.ldap_enabled:
            return False
        return True


@lru_cache
def get_settings() -> Settings:
    return Settings()
