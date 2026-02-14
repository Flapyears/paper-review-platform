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


def test_department_quota_limit(tmp_path: Path):
    db_path = tmp_path / "test4.db"
    storage_dir = tmp_path / "storage4"
    app = create_app(
        database_url=f"sqlite:///{db_path}",
        storage_dir=str(storage_dir),
        max_reviewers_per_department=1,
    )
    client = TestClient(app)

    create = client.post(
        "/api/thesis/my",
        headers=_headers(111, "student"),
        json={"title": "Paper 4"},
    )
    thesis_id = create.json()["data"]["thesis_id"]
    client.post(
        f"/api/thesis/{thesis_id}/upload-final",
        headers=_headers(111, "student"),
        files={"file": ("paper4.pdf", b"paper-v1", "application/pdf")},
    )
    client.post(f"/api/thesis/{thesis_id}/submit-final", headers=_headers(111, "student"))

    failed = client.post(
        "/api/admin/review-tasks/assign",
        headers=_headers(2, "admin"),
        json={"items": [{"thesis_id": thesis_id, "reviewer_ids": [3, 5], "reason": "quota-check"}]},
    )
    assert failed.status_code == 400
    assert "Department quota exceeded" in failed.json()["detail"]

    success = client.post(
        "/api/admin/review-tasks/assign",
        headers=_headers(2, "admin"),
        json={"items": [{"thesis_id": thesis_id, "reviewer_ids": [3, 4], "reason": "cross-dept"}]},
    )
    assert success.status_code == 200


def test_admin_review_task_list_contains_context(tmp_path: Path):
    db_path = tmp_path / "test5.db"
    storage_dir = tmp_path / "storage5"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    create = client.post(
        "/api/thesis/my",
        headers=_headers(201, "student"),
        json={"title": "Paper 5"},
    )
    thesis_id = create.json()["data"]["thesis_id"]
    client.post(
        f"/api/thesis/{thesis_id}/upload-final",
        headers=_headers(201, "student"),
        files={"file": ("paper5.pdf", b"paper-v1", "application/pdf")},
    )
    client.post(f"/api/thesis/{thesis_id}/submit-final", headers=_headers(201, "student"))
    assign = client.post(
        "/api/admin/review-tasks/assign",
        headers=_headers(2, "admin"),
        json={"items": [{"thesis_id": thesis_id, "reviewer_ids": [3], "reason": "task-list"}]},
    )
    task_id = assign.json()["data"]["task_ids"][0]

    resp = client.get("/api/admin/review-tasks", headers=_headers(2, "admin"))
    assert resp.status_code == 200
    rows = resp.json()["items"]
    row = [x for x in rows if x["task_id"] == task_id][0]
    assert row["thesis_id"] == thesis_id
    assert row["thesis_title"] == "Paper 5"
    assert row["reviewer_id"] == 3
    assert row["reviewer_name"] is not None


def test_admin_manage_reviewer_accounts(tmp_path: Path):
    db_path = tmp_path / "test6.db"
    storage_dir = tmp_path / "storage6"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    create = client.post(
        "/api/admin/reviewers",
        headers=_headers(2, "admin"),
        json={
            "username": "reviewer_new",
            "password": "reviewer123",
            "name": "new-reviewer",
            "email": "new-reviewer@example.com",
            "department": "软件系",
        },
    )
    assert create.status_code == 200
    reviewer_id = create.json()["data"]["reviewer_id"]

    listing = client.get("/api/admin/reviewers/manage?q=reviewer_new", headers=_headers(2, "admin"))
    assert listing.status_code == 200
    row = listing.json()["items"][0]
    assert row["id"] == reviewer_id
    assert row["department"] == "软件系"

    update = client.patch(
        f"/api/admin/reviewers/{reviewer_id}",
        headers=_headers(2, "admin"),
        json={"department": "计算机系", "name": "reviewer-updated"},
    )
    assert update.status_code == 200

    toggle = client.post(
        f"/api/admin/reviewers/{reviewer_id}/toggle-active",
        headers=_headers(2, "admin"),
    )
    assert toggle.status_code == 200
    assert toggle.json()["data"]["is_active"] is False

    reset = client.post(
        f"/api/admin/reviewers/{reviewer_id}/reset-password",
        headers=_headers(2, "admin"),
        json={"password": "newpass123"},
    )
    assert reset.status_code == 200


def test_admin_manage_student_accounts(tmp_path: Path):
    db_path = tmp_path / "test7.db"
    storage_dir = tmp_path / "storage7"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    create = client.post(
        "/api/admin/students",
        headers=_headers(2, "admin"),
        json={
            "username": "student_new",
            "password": "student123",
            "name": "new-student",
            "student_no": "20260001",
            "email": "new-student@example.com",
        },
    )
    assert create.status_code == 200
    student_id = create.json()["data"]["student_id"]

    listing = client.get("/api/admin/students/manage?q=20260001", headers=_headers(2, "admin"))
    assert listing.status_code == 200
    row = listing.json()["items"][0]
    assert row["id"] == student_id
    assert row["student_no"] == "20260001"

    update = client.patch(
        f"/api/admin/students/{student_id}",
        headers=_headers(2, "admin"),
        json={"student_no": "20260002", "name": "student-updated"},
    )
    assert update.status_code == 200

    toggle = client.post(
        f"/api/admin/students/{student_id}/toggle-active",
        headers=_headers(2, "admin"),
    )
    assert toggle.status_code == 200
    assert toggle.json()["data"]["is_active"] is False

    reset = client.post(
        f"/api/admin/students/{student_id}/reset-password",
        headers=_headers(2, "admin"),
        json={"password": "newpass123"},
    )
    assert reset.status_code == 200
