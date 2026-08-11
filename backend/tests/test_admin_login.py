from fastapi.testclient import TestClient

from tests.conftest import login


def test_umair_admin_can_manage_users(client: TestClient):
    token = login(client, "umair", "demo123")
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "ADMIN"
    assert me.json()["username"] == "umair"
    assert set(me.json()["regions"]) == {"NORTH", "SOUTH", "CENTRAL"}

    users = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert users.status_code == 200
    assert any(u["username"] == "khurrum" for u in users.json())

    catalog = client.get("/api/auth/access-catalog", headers={"Authorization": f"Bearer {token}"})
    assert catalog.status_code == 200
    assert "NORTH" in catalog.json()["regions"]


def test_admin_login_still_works(client: TestClient):
    token = login(client, "admin", "demo123")
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "ADMIN"
