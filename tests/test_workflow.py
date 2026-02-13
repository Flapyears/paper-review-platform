from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def _headers(user_id: int, role: str) -> dict[str, str]:
    return {"X-User-Id": str(user_id), "X-Role": role, "X-User-Name": f"{role}-{user_id}"}


def test_end_to_end_workflow(tmp_path: Path):
    db_path = tmp_path / "test.db"
    storage_dir = tmp_path / "storage"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    # Student creates thesis and uploads final file.
    resp = client.post(
        "/api/thesis/my",
        headers=_headers(1, "student"),
        json={"title": "My Paper", "advisor_id": 99},
    )
    assert resp.status_code == 200
    thesis_id = resp.json()["data"]["thesis_id"]

    upload = client.post(
        f"/api/thesis/{thesis_id}/upload-final",
        headers=_headers(1, "student"),
        files={"file": ("paper.pdf", b"paper-content", "application/pdf")},
    )
    assert upload.status_code == 200

    submit = client.post(f"/api/thesis/{thesis_id}/submit-final", headers=_headers(1, "student"))
    assert submit.status_code == 200
    assert submit.json()["data"]["thesis_status"] == "SUBMITTED"

    # Admin assigns two reviewers.
    assign = client.post(
        "/api/admin/review-tasks/assign",
        headers=_headers(2, "admin"),
        json={"items": [{"thesis_id": thesis_id, "reviewer_ids": [3, 4], "reason": "default"}]},
    )
    assert assign.status_code == 200
    task_ids = assign.json()["data"]["task_ids"]
    assert len(task_ids) == 2

    # Reviewer 1 submits.
    draft1 = client.put(
        f"/api/reviewer/tasks/{task_ids[0]}/form",
        headers=_headers(3, "reviewer"),
        json={
            "score": 90,
            "grade": "A",
            "allow_defense": "YES",
            "comments": "good",
            "internal_comments": "ok",
        },
    )
    assert draft1.status_code == 200
    submit1 = client.post(f"/api/reviewer/tasks/{task_ids[0]}/submit", headers=_headers(3, "reviewer"))
    assert submit1.status_code == 200

    # Reviewer 2 submits.
    draft2 = client.put(
        f"/api/reviewer/tasks/{task_ids[1]}/form",
        headers=_headers(4, "reviewer"),
        json={
            "score": 85,
            "grade": "B",
            "allow_defense": "YES",
            "comments": "nice",
            "internal_comments": "ok",
        },
    )
    assert draft2.status_code == 200
    submit2 = client.post(f"/api/reviewer/tasks/{task_ids[1]}/submit", headers=_headers(4, "reviewer"))
    assert submit2.status_code == 200

    # Thesis should be marked REVIEW_DONE.
    theses = client.get("/api/admin/thesis", headers=_headers(2, "admin"))
    assert theses.status_code == 200
    thesis = [item for item in theses.json()["items"] if item["id"] == thesis_id][0]
    assert thesis["status"] == "REVIEW_DONE"


def test_return_rework_revision_increment(tmp_path: Path):
    db_path = tmp_path / "test2.db"
    storage_dir = tmp_path / "storage2"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    create = client.post(
        "/api/thesis/my",
        headers=_headers(10, "student"),
        json={"title": "Paper 2"},
    )
    thesis_id = create.json()["data"]["thesis_id"]
    client.post(
        f"/api/thesis/{thesis_id}/upload-final",
        headers=_headers(10, "student"),
        files={"file": ("paper2.pdf", b"paper-v1", "application/pdf")},
    )
    client.post(f"/api/thesis/{thesis_id}/submit-final", headers=_headers(10, "student"))
    assign = client.post(
        "/api/admin/review-tasks/assign",
        headers=_headers(20, "admin"),
        json={"items": [{"thesis_id": thesis_id, "reviewer_ids": [30]}]},
    )
    task_id = assign.json()["data"]["task_ids"][0]

    client.put(
        f"/api/reviewer/tasks/{task_id}/form",
        headers=_headers(30, "reviewer"),
        json={"score": 70, "grade": "C", "allow_defense": "REVISE", "comments": "need fix"},
    )
    client.post(f"/api/reviewer/tasks/{task_id}/submit", headers=_headers(30, "reviewer"))

    returned = client.post(
        f"/api/admin/review-tasks/{task_id}/return",
        headers=_headers(20, "admin"),
        json={"reason": "please rewrite comments"},
    )
    assert returned.status_code == 200

    detail = client.get(f"/api/reviewer/tasks/{task_id}", headers=_headers(30, "reviewer"))
    assert detail.status_code == 200
    assert detail.json()["task"]["status"] == "RETURNED"
    assert detail.json()["form"]["revision_no"] == 2


def test_admin_reviewer_candidates(tmp_path: Path):
    db_path = tmp_path / "test3.db"
    storage_dir = tmp_path / "storage3"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    create = client.post(
        "/api/thesis/my",
        headers=_headers(101, "student"),
        json={"title": "Paper 3", "advisor_id": 3},
    )
    thesis_id = create.json()["data"]["thesis_id"]
    client.post(
        f"/api/thesis/{thesis_id}/upload-final",
        headers=_headers(101, "student"),
        files={"file": ("paper3.pdf", b"paper-v1", "application/pdf")},
    )
    client.post(f"/api/thesis/{thesis_id}/submit-final", headers=_headers(101, "student"))

    candidates = client.get(
        f"/api/admin/reviewers?thesis_id={thesis_id}",
        headers=_headers(2, "admin"),
    )
    assert candidates.status_code == 200
    items = candidates.json()["items"]
    assert len(items) >= 2
    conflicted = [x for x in items if x["id"] == 3][0]
    assert conflicted["is_conflicted"] is True
