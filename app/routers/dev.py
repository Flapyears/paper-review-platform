from datetime import datetime
from enum import Enum
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.database import Base
from app.deps import get_db
from app.models import (
    AuthCredential,
    FileRecord,
    ReviewTask,
    ReviewTaskStatus,
    Thesis,
    ThesisStatus,
    ThesisVersion,
    User,
    UserRole,
)
from app.schemas import MessageResponse
from app.services.auth import hash_password, seed_default_accounts

router = APIRouter(prefix="/api/dev", tags=["dev"])


class SeedUsersRequest(BaseModel):
    students: int = Field(default=10, ge=0, le=500)
    reviewers: int = Field(default=10, ge=0, le=500)
    admins: int = Field(default=0, ge=0, le=20)
    student_thesis_status: str = "NO_THESIS"


class SeedWorkflowRequest(BaseModel):
    students: int = Field(default=10, ge=1, le=500)
    reviewers: int = Field(default=10, ge=2, le=500)
    theses: int = Field(default=10, ge=1, le=500)
    assign_per_thesis: int = Field(default=2, ge=0, le=5)
    submit_thesis: bool = True


class ResetRequest(BaseModel):
    reseed_defaults: bool = True


class StudentThesisSeedStatus(str, Enum):
    NO_THESIS = "NO_THESIS"
    FINAL_UPLOADED = "FINAL_UPLOADED"
    REVIEW_REQUESTED = "REVIEW_REQUESTED"


def _require_dev_enabled(request: Request) -> None:
    if not request.app.state.settings.enable_dev_endpoints:
        raise HTTPException(status_code=404, detail="Dev endpoints are disabled.")


def _next_username(db: Session, prefix: str) -> str:
    used = {
        item[0].lower()
        for item in db.execute(select(AuthCredential.username).where(AuthCredential.username.like(f"{prefix}%"))).all()
    }
    idx = 1
    while True:
        candidate = f"{prefix}{idx}"
        if candidate.lower() not in used:
            return candidate
        idx += 1


def _create_user_with_credential(
    db: Session,
    *,
    role: UserRole,
    name: str,
    username: str,
    password: str,
    department: str | None = None,
    student_no: str | None = None,
) -> User:
    user = User(role=role, name=name, department=department, student_no=student_no)
    db.add(user)
    db.flush()
    db.add(
        AuthCredential(
            user_id=user.id,
            username=username,
            password_hash=hash_password(password),
            is_active=True,
        )
    )
    return user


@router.get("/accounts")
def list_dev_accounts(
    request: Request,
    db: Session = Depends(get_db),
):
    _require_dev_enabled(request)
    creds = db.scalars(select(AuthCredential).order_by(AuthCredential.user_id.asc())).all()
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_([c.user_id for c in creds]))).all()}
    items = []
    for cred in creds:
        user = users.get(cred.user_id)
        if not user:
            continue
        default_password = (
            "student123" if user.role == UserRole.STUDENT else "reviewer123" if user.role == UserRole.REVIEWER else "admin123"
        )
        items.append(
            {
                "user_id": user.id,
                "role": user.role.value,
                "name": user.name,
                "username": cred.username,
                "is_active": cred.is_active,
                "default_password": default_password,
            }
        )
    return {"items": items}


@router.post("/seed/users", response_model=MessageResponse)
def seed_users(
    payload: SeedUsersRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_dev_enabled(request)
    try:
        thesis_seed_status = StudentThesisSeedStatus(payload.student_thesis_status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid student_thesis_status.") from exc
    created: list[dict] = []
    departments = ["计算机系", "软件系", "信息工程系"]
    created_students: list[User] = []

    for i in range(payload.reviewers):
        username = _next_username(db, "reviewer")
        dept = departments[i % len(departments)]
        user = _create_user_with_credential(
            db,
            role=UserRole.REVIEWER,
            name=username,
            username=username,
            password="reviewer123",
            department=dept,
        )
        created.append({"user_id": user.id, "username": username, "role": user.role.value})

    reviewers = db.scalars(select(User).where(User.role == UserRole.REVIEWER).order_by(User.id.asc())).all()
    if thesis_seed_status != StudentThesisSeedStatus.NO_THESIS and not reviewers:
        raise HTTPException(status_code=400, detail="No reviewers available for advisor assignment.")

    for i in range(payload.students):
        username = _next_username(db, "student")
        student_no = f"2026{username.replace('student', '').zfill(4)}"
        user = _create_user_with_credential(
            db,
            role=UserRole.STUDENT,
            name=username,
            username=username,
            password="student123",
            student_no=student_no,
        )
        created_students.append(user)
        created.append({"user_id": user.id, "username": username, "role": user.role.value})

    for _ in range(payload.admins):
        username = _next_username(db, "admin")
        user = _create_user_with_credential(
            db,
            role=UserRole.ADMIN,
            name=username,
            username=username,
            password="admin123",
        )
        created.append({"user_id": user.id, "username": username, "role": user.role.value})

    if thesis_seed_status != StudentThesisSeedStatus.NO_THESIS:
        storage_dir = Path(request.app.state.settings.storage_dir)
        storage_dir.mkdir(parents=True, exist_ok=True)
        for i, student in enumerate(created_students):
            advisor = reviewers[i % len(reviewers)]
            thesis = Thesis(
                student_id=student.id,
                advisor_id=advisor.id,
                title=f"示例论文-{student.name}",
                status=ThesisStatus.DRAFT,
            )
            db.add(thesis)
            db.flush()

            version_no = 1
            filename = f"seed-student-{student.id}-v{version_no}.pdf"
            file_path = storage_dir / filename
            file_path.write_bytes(b"%PDF-1.4\n% Seed file for dev users.\n")
            file_record = FileRecord(
                storage_path=str(file_path.resolve()),
                original_name=filename,
                sha256=f"seed-user-{student.id}-{version_no}",
                mime="application/pdf",
                size=file_path.stat().st_size,
                uploaded_by=student.id,
            )
            db.add(file_record)
            db.flush()

            submit_thesis = thesis_seed_status == StudentThesisSeedStatus.REVIEW_REQUESTED
            version = ThesisVersion(
                thesis_id=thesis.id,
                version_no=version_no,
                stage="final",
                file_id=file_record.id,
                locked_for_review=submit_thesis,
                submitted_at=datetime.utcnow() if submit_thesis else None,
            )
            db.add(version)
            db.flush()
            thesis.current_version_id = version.id
            thesis.status = ThesisStatus.SUBMITTED if submit_thesis else ThesisStatus.DRAFT

    db.commit()
    return MessageResponse(
        message="seed_users_done",
        data={
            "created_count": len(created),
            "created": created,
            "student_thesis_status": thesis_seed_status.value,
        },
    )


@router.post("/seed/workflow", response_model=MessageResponse)
def seed_workflow(
    payload: SeedWorkflowRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_dev_enabled(request)

    # Ensure enough users exist.
    seed_users(
        SeedUsersRequest(students=payload.students, reviewers=payload.reviewers, admins=0),
        request=request,
        db=db,
    )
    admin_user = db.scalar(select(User).where(User.role == UserRole.ADMIN).order_by(User.id.asc()))
    if admin_user is None:
        username = _next_username(db, "admin")
        admin_user = _create_user_with_credential(
            db,
            role=UserRole.ADMIN,
            name=username,
            username=username,
            password="admin123",
        )
        db.commit()

    students = db.scalars(select(User).where(User.role == UserRole.STUDENT).order_by(User.id.asc())).all()
    reviewers = db.scalars(select(User).where(User.role == UserRole.REVIEWER).order_by(User.id.asc())).all()
    storage_dir = Path(request.app.state.settings.storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    created_theses = 0
    created_tasks = 0
    for idx, student in enumerate(students[: payload.theses]):
        thesis = db.scalar(select(Thesis).where(Thesis.student_id == student.id))
        if thesis is None:
            advisor = reviewers[idx % len(reviewers)]
            thesis = Thesis(
                student_id=student.id,
                advisor_id=advisor.id,
                title=f"示例论文-{student.name}",
                status=ThesisStatus.DRAFT,
            )
            db.add(thesis)
            db.flush()
            created_theses += 1

        max_ver = db.scalar(select(ThesisVersion.version_no).where(ThesisVersion.thesis_id == thesis.id).order_by(ThesisVersion.version_no.desc()).limit(1)) or 0
        version_no = max_ver + 1
        filename = f"seed-thesis-{thesis.id}-v{version_no}.pdf"
        file_path = storage_dir / filename
        file_path.write_bytes(b"%PDF-1.4\n% Seed file for dev workflow.\n")
        file_record = FileRecord(
            storage_path=str(file_path.resolve()),
            original_name=filename,
            sha256="seed",
            mime="application/pdf",
            size=file_path.stat().st_size,
            uploaded_by=student.id,
        )
        db.add(file_record)
        db.flush()

        version = ThesisVersion(
            thesis_id=thesis.id,
            version_no=version_no,
            stage="final",
            file_id=file_record.id,
            locked_for_review=payload.submit_thesis,
            submitted_at=datetime.utcnow() if payload.submit_thesis else None,
        )
        db.add(version)
        db.flush()
        thesis.current_version_id = version.id

        if payload.submit_thesis:
            thesis.status = ThesisStatus.SUBMITTED

        if payload.submit_thesis and payload.assign_per_thesis > 0:
            candidate_reviewers = [r for r in reviewers if r.id != thesis.advisor_id]
            selected = candidate_reviewers[: payload.assign_per_thesis]
            for reviewer in selected:
                db.add(
                    ReviewTask(
                        thesis_id=thesis.id,
                        version_id=version.id,
                        reviewer_id=reviewer.id,
                        assigned_by=admin_user.id,
                        status=ReviewTaskStatus.ASSIGNED,
                        assigned_reason="dev-seed",
                    )
                )
                created_tasks += 1
            thesis.status = ThesisStatus.REVIEWING if selected else ThesisStatus.SUBMITTED

    db.commit()
    return MessageResponse(
        message="seed_workflow_done",
        data={
            "theses": created_theses,
            "tasks": created_tasks,
            "students_used": min(len(students), payload.theses),
        },
    )


@router.post("/reset", response_model=MessageResponse)
def reset_dev_data(
    payload: ResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    _require_dev_enabled(request)

    db.execute(text("PRAGMA foreign_keys=OFF"))
    for table in Base.metadata.sorted_tables:
        db.execute(delete(table))
    db.commit()
    db.execute(text("PRAGMA foreign_keys=ON"))

    storage_dir = Path(request.app.state.settings.storage_dir)
    if storage_dir.exists():
        for p in storage_dir.iterdir():
            if p.is_file():
                p.unlink(missing_ok=True)

    if payload.reseed_defaults:
        seed_default_accounts(db)
    return MessageResponse(message="dev_reset_done", data={"reseed_defaults": payload.reseed_defaults})
