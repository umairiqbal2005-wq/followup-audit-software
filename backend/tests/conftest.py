import os

# Must be set before app modules bind the engine.
os.environ["DB_BACKEND"] = "sqlite"
os.environ["SQLITE_PATH"] = "./test_aop.db"
os.environ["LDAP_ENABLED"] = "false"
os.environ["REDIS_ENABLED"] = "false"
os.environ["DISABLE_DEV_BOOTSTRAP"] = "false"
os.environ["APP_ENV"] = "development"

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.services.auth import AuthService


@pytest.fixture(scope="session", autouse=True)
def prepare_database():
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        AuthService(db).ensure_dev_admin()
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_aop.db"):
        os.remove("./test_aop.db")
    get_settings.cache_clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def login(client: TestClient, username: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
