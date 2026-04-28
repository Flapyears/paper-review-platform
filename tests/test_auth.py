from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_login_and_me(tmp_path: Path):
    db_path = tmp_path / "auth.db"
    storage_dir = tmp_path / "storage"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert login.status_code == 200
    token = login.json()["data"]["token"]
    user = login.json()["data"]["user"]
    assert user["role"] == "admin"
    assert user["must_change_password"] is True

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["user"]["role"] == "admin"
    assert me.json()["data"]["user"]["must_change_password"] is True

    change = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "admin", "new_password": "admin123456"},
    )
    assert change.status_code == 200
    assert change.json()["data"]["must_change_password"] is False

    relogin_old = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert relogin_old.status_code == 401

    relogin_new = client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    assert relogin_new.status_code == 200
    assert relogin_new.json()["data"]["user"]["must_change_password"] is False

    logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200

    me_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after.status_code == 401

