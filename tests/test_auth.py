from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_login_and_me(tmp_path: Path):
    db_path = tmp_path / "auth.db"
    storage_dir = tmp_path / "storage"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    login = client.post("/api/auth/login", json={"username": "admin1", "password": "admin123"})
    assert login.status_code == 200
    token = login.json()["data"]["token"]
    user = login.json()["data"]["user"]
    assert user["role"] == "admin"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["user"]["role"] == "admin"

    logout = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200

    me_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after.status_code == 401

