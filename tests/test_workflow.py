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
        json={"title": "My Paper", "advisor_id": 5},
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
        json={"title": "Paper 2", "advisor_id": 4},
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
        json={"title": "Paper 4", "advisor_id": 4},
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
        json={"items": [{"thesis_id": thesis_id, "reviewer_ids": [3, 6], "reason": "cross-dept"}]},
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
        json={"title": "Paper 5", "advisor_id": 4},
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


def test_student_can_load_advisor_list(tmp_path: Path):
    db_path = tmp_path / "test8.db"
    storage_dir = tmp_path / "storage8"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    resp = client.get("/api/thesis/advisors", headers=_headers(1, "student"))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 2
    assert any(item["id"] == 3 for item in items)


def test_student_create_thesis_requires_advisor(tmp_path: Path):
    db_path = tmp_path / "test9.db"
    storage_dir = tmp_path / "storage9"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    resp = client.post(
        "/api/thesis/my",
        headers=_headers(301, "student"),
        json={"title": "No advisor thesis"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Advisor is required."


def test_student_can_update_advisor_in_draft_only(tmp_path: Path):
    db_path = tmp_path / "test10.db"
    storage_dir = tmp_path / "storage10"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    created = client.post(
        "/api/thesis/my",
        headers=_headers(401, "student"),
        json={"title": "Draft thesis", "advisor_id": 3},
    )
    assert created.status_code == 200
    thesis_id = created.json()["data"]["thesis_id"]

    update_draft = client.put(
        f"/api/thesis/{thesis_id}",
        headers=_headers(401, "student"),
        json={"title": "Draft thesis v2", "advisor_id": 4},
    )
    assert update_draft.status_code == 200

    current = client.get("/api/thesis/my", headers=_headers(401, "student"))
    assert current.status_code == 200
    assert current.json()["thesis"]["advisor_id"] == 4

    client.post(
        f"/api/thesis/{thesis_id}/upload-final",
        headers=_headers(401, "student"),
        files={"file": ("paper10.pdf", b"paper-v1", "application/pdf")},
    )
    client.post(f"/api/thesis/{thesis_id}/submit-final", headers=_headers(401, "student"))

    update_submitted = client.put(
        f"/api/thesis/{thesis_id}",
        headers=_headers(401, "student"),
        json={"title": "Draft thesis v3", "advisor_id": 3},
    )
    assert update_submitted.status_code == 400


def test_version_no_is_per_thesis(tmp_path: Path):
    db_path = tmp_path / "test11.db"
    storage_dir = tmp_path / "storage11"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    create1 = client.post(
        "/api/thesis/my",
        headers=_headers(501, "student"),
        json={"title": "Paper A", "advisor_id": 3},
    )
    thesis1 = create1.json()["data"]["thesis_id"]
    upload1 = client.post(
        f"/api/thesis/{thesis1}/upload-final",
        headers=_headers(501, "student"),
        files={"file": ("a.pdf", b"a-v1", "application/pdf")},
    )
    assert upload1.status_code == 200
    assert upload1.json()["data"]["version_no"] == 1

    create2 = client.post(
        "/api/thesis/my",
        headers=_headers(502, "student"),
        json={"title": "Paper B", "advisor_id": 4},
    )
    thesis2 = create2.json()["data"]["thesis_id"]
    upload2 = client.post(
        f"/api/thesis/{thesis2}/upload-final",
        headers=_headers(502, "student"),
        files={"file": ("b.pdf", b"b-v1", "application/pdf")},
    )
    assert upload2.status_code == 200
    assert upload2.json()["data"]["version_no"] == 1


def test_dev_seed_endpoints(tmp_path: Path):
    db_path = tmp_path / "test12.db"
    storage_dir = tmp_path / "storage12"
    app = create_app(database_url=f"sqlite:///{db_path}", storage_dir=str(storage_dir))
    client = TestClient(app)

    seed_users = client.post("/api/dev/seed/users", json={"students": 2, "reviewers": 2, "admins": 0})
    assert seed_users.status_code == 200
    assert seed_users.json()["data"]["created_count"] >= 4

    seed_workflow = client.post(
        "/api/dev/seed/workflow",
        json={"students": 2, "reviewers": 2, "theses": 2, "assign_per_thesis": 1, "submit_thesis": True},
    )
    assert seed_workflow.status_code == 200

    accounts = client.get("/api/dev/accounts")
    assert accounts.status_code == 200
    assert len(accounts.json()["items"]) >= 4

    reset = client.post("/api/dev/reset", json={"reseed_defaults": True})
    assert reset.status_code == 200
