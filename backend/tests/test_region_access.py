from fastapi.testclient import TestClient

from tests.conftest import login


def test_admin_assigns_north_region_and_user_is_scoped(client: TestClient):
    admin = login(client, "admin", "Admin@123")
    khurrum = login(client, "khurrum", "Pass@123")

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {khurrum}"})
    assert me.status_code == 200
    assert me.json()["regions"] == ["NORTH"]
    assert "BRANCH_AUDIT" in me.json()["segments"]

    north = client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {admin}"},
        data={
            "title": "North Branch Review",
            "report_number": "RPT-N-001",
            "region": "NORTH",
            "segment": "BRANCH_AUDIT",
        },
    )
    assert north.status_code == 201, north.text
    south = client.post(
        "/api/reports",
        headers={"Authorization": f"Bearer {admin}"},
        data={
            "title": "South Shariah Review",
            "report_number": "RPT-S-001",
            "region": "SOUTH",
            "segment": "SHARIAH",
        },
    )
    assert south.status_code == 201, south.text

    north_obs = client.post(
        "/api/observations",
        headers={"Authorization": f"Bearer {admin}"},
        json={
            "report_id": north.json()["id"],
            "title": "North finding",
            "description": "Branch control gap",
            "severity": "HIGH",
        },
    )
    assert north_obs.status_code == 201, north_obs.text
    south_obs = client.post(
        "/api/observations",
        headers={"Authorization": f"Bearer {admin}"},
        json={
            "report_id": south.json()["id"],
            "title": "South finding",
            "description": "Shariah note",
            "severity": "MEDIUM",
        },
    )
    assert south_obs.status_code == 201, south_obs.text

    visible = client.get("/api/observations", headers={"Authorization": f"Bearer {khurrum}"})
    assert visible.status_code == 200
    titles = {row["title"] for row in visible.json()}
    assert "North finding" in titles
    assert "South finding" not in titles

    denied = client.get(
        f"/api/observations/{south_obs.json()['id']}",
        headers={"Authorization": f"Bearer {khurrum}"},
    )
    assert denied.status_code == 403

    reports = client.get("/api/reports", headers={"Authorization": f"Bearer {khurrum}"})
    assert reports.status_code == 200
    nums = {r["report_number"] for r in reports.json()}
    assert "RPT-N-001" in nums
    assert "RPT-S-001" not in nums


def test_admin_can_reassign_user_regions(client: TestClient):
    admin = login(client, "admin", "Admin@123")
    users = client.get("/api/users", headers={"Authorization": f"Bearer {admin}"})
    south_user = next(u for u in users.json() if u["username"] == "south_viewer")

    updated = client.patch(
        f"/api/users/{south_user['id']}",
        headers={"Authorization": f"Bearer {admin}"},
        json={
            "role": "VIEWER",
            "regions": ["SOUTH", "CENTRAL"],
            "segments": ["SHARIAH", "MANAGEMENT"],
        },
    )
    assert updated.status_code == 200, updated.text
    assert set(updated.json()["regions"]) == {"SOUTH", "CENTRAL"}
    assert set(updated.json()["segments"]) == {"SHARIAH", "MANAGEMENT"}
