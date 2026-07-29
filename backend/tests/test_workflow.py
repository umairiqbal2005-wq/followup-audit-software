import os

# Ensure sqlite before app imports bind the engine
os.environ.setdefault("DB_BACKEND", "sqlite")
os.environ.setdefault("SQLITE_PATH", "./test_aop.db")
os.environ.setdefault("LDAP_ENABLED", "false")
os.environ.setdefault("REDIS_ENABLED", "false")

from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.services.auth import AuthService


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        AuthService(db).ensure_dev_admin()
    finally:
        db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_aop.db"):
        os.remove("./test_aop.db")


def _client():
    return TestClient(app)


def _login(client: TestClient, username: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_health():
    with _client() as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_login_and_me():
    with _client() as client:
        token = _login(client, "admin", "Admin@123")
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "ADMIN"


def test_observation_workflow():
    with _client() as client:
        admin = _login(client, "admin", "Admin@123")
        central = _login(client, "central1", "Pass@123")
        owner = _login(client, "owner1", "Pass@123")

        report = client.post(
            "/api/reports",
            headers={"Authorization": f"Bearer {admin}"},
            data={"title": "Q1 Audit", "report_number": "RPT-2026-001", "description": "Test"},
        )
        assert report.status_code == 201, report.text
        report_id = report.json()["id"]

        obs = client.post(
            "/api/observations",
            headers={"Authorization": f"Bearer {central}"},
            json={
                "report_id": report_id,
                "title": "Access control gap",
                "description": "Segregation of duties missing",
                "severity": "HIGH",
                "category": "ITGC",
            },
        )
        assert obs.status_code == 201, obs.text
        obs_id = obs.json()["id"]
        assert obs.json()["status"] == "DRAFT"

        submitted = client.post(
            f"/api/observations/{obs_id}/submit",
            headers={"Authorization": f"Bearer {central}"},
        )
        assert submitted.status_code == 200
        assert submitted.json()["status"] == "PENDING_REVIEW"

        users = client.get("/api/users?role=PROCESS_OWNER", headers={"Authorization": f"Bearer {central}"})
        assert users.status_code == 200
        owner_id = users.json()[0]["id"]

        assigned = client.post(
            f"/api/observations/{obs_id}/assign",
            headers={"Authorization": f"Bearer {central}"},
            json={"owner_id": owner_id, "notes": "Please remediate"},
        )
        assert assigned.status_code == 200
        assert assigned.json()["status"] == "ASSIGNED"

        responded = client.post(
            f"/api/observations/{obs_id}/respond",
            headers={"Authorization": f"Bearer {owner}"},
            json={"response_type": "RESOLVED", "comments": "Fixed and evidenced"},
        )
        assert responded.status_code == 200
        assert responded.json()["status"] == "PENDING_VERIFICATION"

        closed = client.post(
            f"/api/observations/{obs_id}/verify",
            headers={"Authorization": f"Bearer {central}"},
            json={"approved": True, "notes": "Looks good"},
        )
        assert closed.status_code == 200
        assert closed.json()["status"] == "CLOSED"

        dash = client.get("/api/observations/dashboard", headers={"Authorization": f"Bearer {admin}"})
        assert dash.status_code == 200
        assert dash.json()["closed"] >= 1
