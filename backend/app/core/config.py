from functools import lru_cache
from typing import List

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

    dev_admin_username: str = "admin"
    dev_admin_password: str = "Admin@123"
    dev_admin_email: str = "admin@example.com"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        if self.db_backend.lower() == "oracle":
            return (
                f"oracle+oracledb://{self.oracle_user}:{self.oracle_password}@"
                f"{self.oracle_dsn}"
            )
        return f"sqlite:///{self.sqlite_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
