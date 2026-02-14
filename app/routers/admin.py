from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import (
    AuthCredential,
    ReviewForm,
    ReviewFormHistory,
    ReviewTask,
    ReviewTaskStatus,
    Thesis,
    ThesisStatus,
    ThesisVersion,
    User,
    UserRole,
)
from app.schemas import (
    AutoAssignRequest,
    AssignRequest,
    CancelRequest,
    MessageResponse,
    ReviewerCreateRequest,
    ReviewerResetPasswordRequest,
    ReviewerUpdateRequest,
    StudentCreateRequest,
    StudentResetPasswordRequest,
    StudentUpdateRequest,
    ReplaceRequest,
    ReturnRequest,
)
from app.services.audit import write_audit_log
from app.services.auth import hash_password
from app.services.state_machine import refresh_thesis_status_from_tasks

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _normalize_department(value: str | None) -> str:
    department = (value or "").strip()
    return department or "未设置科室"


def _load_user_department_map(db: Session, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(user_ids))).all()
    return {user.id: _normalize_department(user.department) for user in users}


def _count_departments(department_names: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in department_names:
        counts[name] = counts.get(name, 0) + 1
    return counts


def _validate_department_quota(
    *,
    db: Session,
    thesis_id: int,
    new_reviewer_ids: set[int],
    max_per_department: int,
    exclude_task_id: int | None = None,
) -> None:
    if max_per_department <= 0:
        return

    existing_task_query = select(ReviewTask).where(
        ReviewTask.thesis_id == thesis_id,
        ReviewTask.status != ReviewTaskStatus.CANCELLED,
    )
    if exclude_task_id is not None:
        existing_task_query = existing_task_query.where(ReviewTask.id != exclude_task_id)
    existing_tasks = db.scalars(existing_task_query).all()

    reviewer_ids = {task.reviewer_id for task in existing_tasks}.union(new_reviewer_ids)
    department_map = _load_user_department_map(db, reviewer_ids)
    department_list = [department_map.get(reviewer_id, "未设置科室") for reviewer_id in reviewer_ids]
    department_counts = _count_departments(department_list)
    exceeded = [dept for dept, count in department_counts.items() if count > max_per_department]
    if exceeded:
        dept = exceeded[0]
        raise HTTPException(
            status_code=400,
            detail=(
                f"Department quota exceeded: {dept} has {department_counts[dept]} reviewers, "
                f"max allowed is {max_per_department}."
            ),
        )


@router.get("/reviewers")
def list_reviewer_candidates(
    request: Request,
    thesis_id: int | None = None,
    q: str | None = None,
    max_task_limit: int = 8,
    max_per_department: int | None = Query(default=None, ge=1, le=10),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    thesis = db.get(Thesis, thesis_id) if thesis_id else None
    if thesis_id and thesis is None:
        raise HTTPException(status_code=404, detail="Thesis not found.")
    max_per_department = (
        max_per_department
        if max_per_department is not None
        else request.app.state.settings.max_reviewers_per_department
    )

    thesis_department_counts: dict[str, int] = {}
    if thesis:
        assigned_reviewer_ids = set(
            db.scalars(
                select(ReviewTask.reviewer_id).where(
                    ReviewTask.thesis_id == thesis.id,
                    ReviewTask.status != ReviewTaskStatus.CANCELLED,
                )
            ).all()
        )
        thesis_department_counts = _count_departments(
            list(_load_user_department_map(db, assigned_reviewer_ids).values())
        )

    reviewers = db.scalars(select(User).where(User.role == UserRole.REVIEWER).order_by(User.id.asc())).all()
    rows: list[dict] = []
    keyword = (q or "").strip().lower()
    for reviewer in reviewers:
        if keyword and keyword not in reviewer.name.lower() and keyword not in str(reviewer.id):
            continue
        active_tasks = db.scalar(
            select(func.count(ReviewTask.id)).where(
                ReviewTask.reviewer_id == reviewer.id,
                ReviewTask.status.in_(
                    [
                        ReviewTaskStatus.ASSIGNED,
                        ReviewTaskStatus.DRAFTING,
                        ReviewTaskStatus.RETURNED,
                    ]
                ),
            )
        ) or 0
        submitted_tasks = db.scalar(
            select(func.count(ReviewTask.id)).where(
                ReviewTask.reviewer_id == reviewer.id,
                ReviewTask.status == ReviewTaskStatus.SUBMITTED,
            )
        ) or 0
        latest_assigned_at = db.scalar(
            select(func.max(ReviewTask.created_at)).where(ReviewTask.reviewer_id == reviewer.id)
        )
        department = _normalize_department(reviewer.department)
        dept_assigned_count = thesis_department_counts.get(department, 0)
        dept_remaining_slots = max(0, max_per_department - dept_assigned_count)
        dept_will_exceed_quota = dept_assigned_count + 1 > max_per_department
        is_conflicted = bool(thesis and thesis.advisor_id and reviewer.id == thesis.advisor_id)
        available_slots = max(0, max_task_limit - active_tasks)
        recommendation_score = available_slots - (5 if is_conflicted else 0) - (3 if dept_will_exceed_quota else 0)
        rows.append(
            {
                "id": reviewer.id,
                "name": reviewer.name,
                "email": reviewer.email,
                "department": department,
                "active_task_count": active_tasks,
                "submitted_task_count": submitted_tasks,
                "max_task_limit": max_task_limit,
                "available_slots": available_slots,
                "is_conflicted": is_conflicted,
                "conflict_reason": "导师回避冲突" if is_conflicted else None,
                "department_assigned_count": dept_assigned_count,
                "department_max_limit": max_per_department,
                "department_remaining_slots": dept_remaining_slots,
                "department_will_exceed_quota": dept_will_exceed_quota,
                "latest_assigned_at": latest_assigned_at.isoformat() if latest_assigned_at else None,
                "recommendation_score": recommendation_score,
            }
        )
    rows.sort(
        key=lambda x: (
            x["is_conflicted"],
            x["department_will_exceed_quota"],
            -x["recommendation_score"],
            x["active_task_count"],
            x["id"],
        )
    )
    return {"items": rows}


def _reviewer_candidates_for_thesis(
    *,
    db: Session,
    thesis: Thesis,
    max_per_department: int,
    max_task_limit: int,
) -> list[dict]:
    thesis_department_counts: dict[str, int] = {}
    assigned_reviewer_ids = set(
        db.scalars(
            select(ReviewTask.reviewer_id).where(
                ReviewTask.thesis_id == thesis.id,
                ReviewTask.status != ReviewTaskStatus.CANCELLED,
            )
        ).all()
    )
    thesis_department_counts = _count_departments(
        list(_load_user_department_map(db, assigned_reviewer_ids).values())
    )

    reviewers = db.scalars(select(User).where(User.role == UserRole.REVIEWER).order_by(User.id.asc())).all()
    rows: list[dict] = []
    for reviewer in reviewers:
        active_tasks = db.scalar(
            select(func.count(ReviewTask.id)).where(
                ReviewTask.reviewer_id == reviewer.id,
                ReviewTask.status.in_(
                    [
                        ReviewTaskStatus.ASSIGNED,
                        ReviewTaskStatus.DRAFTING,
                        ReviewTaskStatus.RETURNED,
                    ]
                ),
            )
        ) or 0
        submitted_tasks = db.scalar(
            select(func.count(ReviewTask.id)).where(
                ReviewTask.reviewer_id == reviewer.id,
                ReviewTask.status == ReviewTaskStatus.SUBMITTED,
            )
        ) or 0
        latest_assigned_at = db.scalar(
            select(func.max(ReviewTask.created_at)).where(ReviewTask.reviewer_id == reviewer.id)
        )
        department = _normalize_department(reviewer.department)
        dept_assigned_count = thesis_department_counts.get(department, 0)
        dept_remaining_slots = max(0, max_per_department - dept_assigned_count)
        dept_will_exceed_quota = dept_assigned_count + 1 > max_per_department
        is_conflicted = bool(thesis.advisor_id and reviewer.id == thesis.advisor_id)
        available_slots = max(0, max_task_limit - active_tasks)
        recommendation_score = available_slots - (5 if is_conflicted else 0) - (3 if dept_will_exceed_quota else 0)
        rows.append(
            {
                "id": reviewer.id,
                "name": reviewer.name,
                "email": reviewer.email,
                "department": department,
                "active_task_count": active_tasks,
                "submitted_task_count": submitted_tasks,
                "max_task_limit": max_task_limit,
                "available_slots": available_slots,
                "is_conflicted": is_conflicted,
                "conflict_reason": "导师回避冲突" if is_conflicted else None,
                "department_assigned_count": dept_assigned_count,
                "department_max_limit": max_per_department,
                "department_remaining_slots": dept_remaining_slots,
                "department_will_exceed_quota": dept_will_exceed_quota,
                "latest_assigned_at": latest_assigned_at.isoformat() if latest_assigned_at else None,
                "recommendation_score": recommendation_score,
            }
        )
    rows.sort(
        key=lambda x: (
            x["is_conflicted"],
            x["department_will_exceed_quota"],
            -x["recommendation_score"],
            x["active_task_count"],
            x["id"],
        )
    )
    return rows


@router.get("/reviewers/manage")
def list_reviewers_manage(
    q: str | None = None,
    department: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    query = select(User).where(User.role == UserRole.REVIEWER)
    if department:
        query = query.where(User.department == department)
    reviewers = db.scalars(query.order_by(User.id.asc())).all()
    keyword = (q or "").strip().lower()
    rows = []
    for reviewer in reviewers:
        credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == reviewer.id))
        active = bool(credential and credential.is_active)
        if is_active is not None and active != is_active:
            continue
        if keyword and keyword not in reviewer.name.lower() and keyword not in str(reviewer.id):
            username = (credential.username if credential else "").lower()
            if keyword not in username:
                continue
        active_tasks = db.scalar(
            select(func.count(ReviewTask.id)).where(
                ReviewTask.reviewer_id == reviewer.id,
                ReviewTask.status.in_(
                    [ReviewTaskStatus.ASSIGNED, ReviewTaskStatus.DRAFTING, ReviewTaskStatus.RETURNED]
                ),
            )
        ) or 0
        submitted_tasks = db.scalar(
            select(func.count(ReviewTask.id)).where(
                ReviewTask.reviewer_id == reviewer.id,
                ReviewTask.status == ReviewTaskStatus.SUBMITTED,
            )
        ) or 0
        rows.append(
            {
                "id": reviewer.id,
                "name": reviewer.name,
                "email": reviewer.email,
                "department": _normalize_department(reviewer.department),
                "username": credential.username if credential else None,
                "is_active": active,
                "active_task_count": active_tasks,
                "submitted_task_count": submitted_tasks,
                "created_at": reviewer.created_at.isoformat(),
            }
        )
    return {"items": rows}


@router.post("/reviewers", response_model=MessageResponse)
def create_reviewer(
    payload: ReviewerCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    username = payload.username.strip()
    exists = db.scalar(select(AuthCredential).where(AuthCredential.username == username))
    if exists:
        raise HTTPException(status_code=400, detail="Username already exists.")
    reviewer = User(
        role=UserRole.REVIEWER,
        name=payload.name.strip(),
        email=(payload.email or "").strip() or None,
        department=(payload.department or "").strip() or None,
    )
    db.add(reviewer)
    db.flush()
    credential = AuthCredential(
        user_id=reviewer.id,
        username=username,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(credential)
    write_audit_log(
        db,
        user.id,
        "reviewer_create",
        "user",
        str(reviewer.id),
        payload={"username": username, "department": reviewer.department},
    )
    db.commit()
    return MessageResponse(message="reviewer_created", data={"reviewer_id": reviewer.id})


@router.patch("/reviewers/{reviewer_id}", response_model=MessageResponse)
def update_reviewer(
    reviewer_id: int,
    payload: ReviewerUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    reviewer = db.get(User, reviewer_id)
    if reviewer is None or reviewer.role != UserRole.REVIEWER:
        raise HTTPException(status_code=404, detail="Reviewer not found.")
    if payload.name is not None:
        reviewer.name = payload.name.strip()
    if payload.email is not None:
        reviewer.email = (payload.email or "").strip() or None
    if payload.department is not None:
        reviewer.department = (payload.department or "").strip() or None
    write_audit_log(db, user.id, "reviewer_update", "user", str(reviewer.id))
    db.commit()
    return MessageResponse(message="reviewer_updated")


@router.post("/reviewers/{reviewer_id}/toggle-active", response_model=MessageResponse)
def toggle_reviewer_active(
    reviewer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    reviewer = db.get(User, reviewer_id)
    if reviewer is None or reviewer.role != UserRole.REVIEWER:
        raise HTTPException(status_code=404, detail="Reviewer not found.")
    credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == reviewer.id))
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found.")
    credential.is_active = not credential.is_active
    write_audit_log(
        db,
        user.id,
        "reviewer_toggle_active",
        "user",
        str(reviewer.id),
        payload={"is_active": credential.is_active},
    )
    db.commit()
    return MessageResponse(message="reviewer_active_toggled", data={"is_active": credential.is_active})


@router.post("/reviewers/{reviewer_id}/reset-password", response_model=MessageResponse)
def reset_reviewer_password(
    reviewer_id: int,
    payload: ReviewerResetPasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    reviewer = db.get(User, reviewer_id)
    if reviewer is None or reviewer.role != UserRole.REVIEWER:
        raise HTTPException(status_code=404, detail="Reviewer not found.")
    credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == reviewer.id))
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found.")
    credential.password_hash = hash_password(payload.password)
    write_audit_log(db, user.id, "reviewer_reset_password", "user", str(reviewer.id))
    db.commit()
    return MessageResponse(message="reviewer_password_reset")


@router.get("/students/manage")
def list_students_manage(
    q: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    students = db.scalars(select(User).where(User.role == UserRole.STUDENT).order_by(User.id.asc())).all()
    keyword = (q or "").strip().lower()
    rows = []
    for student in students:
        credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == student.id))
        active = bool(credential and credential.is_active)
        if is_active is not None and active != is_active:
            continue
        if keyword:
            username = (credential.username if credential else "").lower()
            if (
                keyword not in student.name.lower()
                and keyword not in str(student.id)
                and keyword not in (student.student_no or "").lower()
                and keyword not in username
            ):
                continue
        thesis_count = db.scalar(select(func.count(Thesis.id)).where(Thesis.student_id == student.id)) or 0
        rows.append(
            {
                "id": student.id,
                "name": student.name,
                "student_no": student.student_no,
                "email": student.email,
                "username": credential.username if credential else None,
                "is_active": active,
                "thesis_count": thesis_count,
                "created_at": student.created_at.isoformat(),
            }
        )
    return {"items": rows}


@router.post("/students", response_model=MessageResponse)
def create_student(
    payload: StudentCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    username = payload.username.strip()
    if db.scalar(select(AuthCredential).where(AuthCredential.username == username)):
        raise HTTPException(status_code=400, detail="Username already exists.")
    student_no = (payload.student_no or "").strip() or None
    if student_no and db.scalar(select(User).where(User.student_no == student_no)):
        raise HTTPException(status_code=400, detail="Student number already exists.")
    student = User(
        role=UserRole.STUDENT,
        name=payload.name.strip(),
        student_no=student_no,
        email=(payload.email or "").strip() or None,
    )
    db.add(student)
    db.flush()
    credential = AuthCredential(
        user_id=student.id,
        username=username,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(credential)
    write_audit_log(
        db,
        user.id,
        "student_create",
        "user",
        str(student.id),
        payload={"username": username, "student_no": student.student_no},
    )
    db.commit()
    return MessageResponse(message="student_created", data={"student_id": student.id})


@router.patch("/students/{student_id}", response_model=MessageResponse)
def update_student(
    student_id: int,
    payload: StudentUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    student = db.get(User, student_id)
    if student is None or student.role != UserRole.STUDENT:
        raise HTTPException(status_code=404, detail="Student not found.")
    if payload.name is not None:
        student.name = payload.name.strip()
    if payload.student_no is not None:
        student_no = (payload.student_no or "").strip() or None
        if student_no:
            conflict = db.scalar(select(User).where(User.student_no == student_no, User.id != student.id))
            if conflict:
                raise HTTPException(status_code=400, detail="Student number already exists.")
        student.student_no = student_no
    if payload.email is not None:
        student.email = (payload.email or "").strip() or None
    write_audit_log(db, user.id, "student_update", "user", str(student.id))
    db.commit()
    return MessageResponse(message="student_updated")


@router.post("/students/{student_id}/toggle-active", response_model=MessageResponse)
def toggle_student_active(
    student_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    student = db.get(User, student_id)
    if student is None or student.role != UserRole.STUDENT:
        raise HTTPException(status_code=404, detail="Student not found.")
    credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == student.id))
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found.")
    credential.is_active = not credential.is_active
    write_audit_log(
        db,
        user.id,
        "student_toggle_active",
        "user",
        str(student.id),
        payload={"is_active": credential.is_active},
    )
    db.commit()
    return MessageResponse(message="student_active_toggled", data={"is_active": credential.is_active})


@router.post("/students/{student_id}/reset-password", response_model=MessageResponse)
def reset_student_password(
    student_id: int,
    payload: StudentResetPasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    student = db.get(User, student_id)
    if student is None or student.role != UserRole.STUDENT:
        raise HTTPException(status_code=404, detail="Student not found.")
    credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == student.id))
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found.")
    credential.password_hash = hash_password(payload.password)
    write_audit_log(db, user.id, "student_reset_password", "user", str(student.id))
    db.commit()
    return MessageResponse(message="student_password_reset")


@router.get("/thesis")
def list_thesis(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    query = select(Thesis)
    if status:
        try:
            thesis_status = ThesisStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid status") from exc
        query = query.where(Thesis.status == thesis_status)

    theses = db.scalars(query.order_by(Thesis.created_at.desc())).all()
    version_ids = {t.current_version_id for t in theses if t.current_version_id}
    version_map = (
        {v.id: v for v in db.scalars(select(ThesisVersion).where(ThesisVersion.id.in_(version_ids))).all()}
        if version_ids
        else {}
    )
    rows = []
    for thesis in theses:
        assigned_count = db.scalar(
            select(func.count(ReviewTask.id)).where(
                ReviewTask.thesis_id == thesis.id,
                ReviewTask.status != ReviewTaskStatus.CANCELLED,
            )
        )
        rows.append(
            {
                "id": thesis.id,
                "title": thesis.title,
                "student_id": thesis.student_id,
                "status": thesis.status.value,
                "current_version_id": thesis.current_version_id,
                "current_version_no": (
                    version_map[thesis.current_version_id].version_no
                    if thesis.current_version_id and thesis.current_version_id in version_map
                    else None
                ),
                "assigned_count": assigned_count or 0,
                "created_at": thesis.created_at.isoformat(),
            }
        )
    return {"items": rows}


@router.get("/review-tasks")
def list_review_tasks(
    status: str | None = None,
    thesis_id: int | None = None,
    reviewer_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    query = select(ReviewTask)
    if status:
        try:
            task_status = ReviewTaskStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid status") from exc
        query = query.where(ReviewTask.status == task_status)
    if thesis_id is not None:
        query = query.where(ReviewTask.thesis_id == thesis_id)
    if reviewer_id is not None:
        query = query.where(ReviewTask.reviewer_id == reviewer_id)

    tasks = db.scalars(query.order_by(ReviewTask.updated_at.desc())).all()
    thesis_ids = {task.thesis_id for task in tasks}
    thesis_map = (
        {thesis.id: thesis for thesis in db.scalars(select(Thesis).where(Thesis.id.in_(thesis_ids))).all()}
        if thesis_ids
        else {}
    )
    user_ids = {task.reviewer_id for task in tasks}.union({task.assigned_by for task in tasks})
    user_map = (
        {u.id: u for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()} if user_ids else {}
    )

    rows = []
    for task in tasks:
        thesis = thesis_map.get(task.thesis_id)
        reviewer = user_map.get(task.reviewer_id)
        assigner = user_map.get(task.assigned_by)
        rows.append(
            {
                "task_id": task.id,
                "status": task.status.value,
                "thesis_id": task.thesis_id,
                "thesis_title": thesis.title if thesis else None,
                "reviewer_id": task.reviewer_id,
                "reviewer_name": reviewer.name if reviewer else None,
                "reviewer_department": _normalize_department(reviewer.department if reviewer else None),
                "assigned_by": task.assigned_by,
                "assigned_by_name": assigner.name if assigner else None,
                "assigned_reason": task.assigned_reason,
                "due_at": task.due_at.isoformat() if task.due_at else None,
                "return_reason": task.return_reason,
                "cancelled_reason": task.cancelled_reason,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }
        )
    return {"items": rows}


@router.post("/thesis/{thesis_id}/return", response_model=MessageResponse)
def return_thesis(
    thesis_id: int,
    payload: ReturnRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    thesis = db.get(Thesis, thesis_id)
    if thesis is None:
        raise HTTPException(status_code=404, detail="Thesis not found.")
    if thesis.status != ThesisStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Only SUBMITTED thesis can be returned.")

    thesis.status = ThesisStatus.DRAFT
    thesis.return_reason = payload.reason.strip()
    write_audit_log(
        db,
        user.id,
        "thesis_return",
        "thesis",
        str(thesis.id),
        payload={"reason": payload.reason.strip()},
    )
    db.commit()
    return MessageResponse(message="returned_to_draft")


@router.post("/review-tasks/assign", response_model=MessageResponse)
def assign_review_tasks(
    request: Request,
    payload: AssignRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    max_per_department = (
        payload.max_reviewers_per_department
        if payload.max_reviewers_per_department is not None
        else request.app.state.settings.max_reviewers_per_department
    )
    created_task_ids: list[int] = []
    for item in payload.items:
        thesis = db.get(Thesis, item.thesis_id)
        if thesis is None:
            raise HTTPException(status_code=404, detail=f"Thesis {item.thesis_id} not found.")
        if thesis.status != ThesisStatus.SUBMITTED:
            raise HTTPException(
                status_code=400, detail=f"Thesis {item.thesis_id} is not SUBMITTED."
            )
        if thesis.current_version_id is None:
            raise HTTPException(status_code=400, detail="Thesis current version is missing.")

        reviewer_ids = set(item.reviewer_ids)
        for reviewer_id in reviewer_ids:
            reviewer = db.get(User, reviewer_id)
            if reviewer is None:
                reviewer = User(
                    id=reviewer_id,
                    role=UserRole.REVIEWER,
                    name=f"reviewer-{reviewer_id}",
                    department=None,
                )
                db.add(reviewer)
                db.flush()
            elif reviewer.role != UserRole.REVIEWER:
                raise HTTPException(
                    status_code=400, detail=f"User {reviewer_id} is not a reviewer."
                )
            if thesis.advisor_id and reviewer_id == thesis.advisor_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Reviewer {reviewer_id} conflicts with advisor for thesis {thesis.id}.",
                )

        _validate_department_quota(
            db=db,
            thesis_id=thesis.id,
            new_reviewer_ids=reviewer_ids,
            max_per_department=max_per_department,
        )

        for reviewer_id in reviewer_ids:
            task = ReviewTask(
                thesis_id=thesis.id,
                version_id=thesis.current_version_id,
                reviewer_id=reviewer_id,
                assigned_by=user.id,
                status=ReviewTaskStatus.ASSIGNED,
                assigned_reason=item.reason,
                due_at=payload.due_at,
            )
            db.add(task)
            db.flush()
            created_task_ids.append(task.id)
            write_audit_log(
                db,
                user.id,
                "review_task_assign",
                "review_task",
                str(task.id),
                payload={"thesis_id": thesis.id, "reviewer_id": reviewer_id, "reason": item.reason},
            )

        thesis.status = ThesisStatus.REVIEWING

    db.commit()
    return MessageResponse(message="assigned", data={"task_ids": created_task_ids})


@router.post("/review-tasks/auto-assign", response_model=MessageResponse)
def auto_assign_review_tasks(
    request: Request,
    payload: AutoAssignRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    max_per_department = (
        payload.max_reviewers_per_department
        if payload.max_reviewers_per_department is not None
        else request.app.state.settings.max_reviewers_per_department
    )
    theses = db.scalars(select(Thesis).where(Thesis.status == ThesisStatus.SUBMITTED).order_by(Thesis.id.asc())).all()
    created_task_ids: list[int] = []
    assigned_thesis_ids: list[int] = []
    skipped: list[dict] = []

    for thesis in theses:
        try:
            if thesis.current_version_id is None:
                skipped.append({"thesis_id": thesis.id, "reason": "missing_current_version"})
                continue
            existing_task_count = db.scalar(
                select(func.count(ReviewTask.id)).where(
                    ReviewTask.thesis_id == thesis.id,
                    ReviewTask.status != ReviewTaskStatus.CANCELLED,
                )
            ) or 0
            if existing_task_count > 0:
                skipped.append({"thesis_id": thesis.id, "reason": "already_assigned"})
                continue

            candidates = _reviewer_candidates_for_thesis(
                db=db,
                thesis=thesis,
                max_per_department=max_per_department,
                max_task_limit=payload.max_task_limit,
            )
            dept_counts: dict[str, int] = {}
            chosen: list[int] = []
            for row in candidates:
                if row["is_conflicted"] or row["available_slots"] <= 0:
                    continue
                department = row["department"]
                if max_per_department > 0 and dept_counts.get(department, 0) >= max_per_department:
                    continue
                chosen.append(row["id"])
                dept_counts[department] = dept_counts.get(department, 0) + 1
                if len(chosen) >= payload.reviewers_per_thesis:
                    break
            if len(chosen) < payload.reviewers_per_thesis:
                skipped.append({"thesis_id": thesis.id, "reason": "insufficient_reviewers"})
                continue

            _validate_department_quota(
                db=db,
                thesis_id=thesis.id,
                new_reviewer_ids=set(chosen),
                max_per_department=max_per_department,
            )

            for reviewer_id in chosen:
                task = ReviewTask(
                    thesis_id=thesis.id,
                    version_id=thesis.current_version_id,
                    reviewer_id=reviewer_id,
                    assigned_by=user.id,
                    status=ReviewTaskStatus.ASSIGNED,
                    assigned_reason=payload.reason or "auto_assign_unassigned",
                )
                db.add(task)
                db.flush()
                created_task_ids.append(task.id)
                write_audit_log(
                    db,
                    user.id,
                    "review_task_auto_assign",
                    "review_task",
                    str(task.id),
                    payload={"thesis_id": thesis.id, "reviewer_id": reviewer_id},
                )
            thesis.status = ThesisStatus.REVIEWING
            assigned_thesis_ids.append(thesis.id)
        except HTTPException as exc:
            skipped.append({"thesis_id": thesis.id, "reason": f"auto_assign_error:{exc.detail}"})
            continue

    db.commit()
    return MessageResponse(
        message="auto_assigned",
        data={
            "assigned_thesis_ids": assigned_thesis_ids,
            "created_task_ids": created_task_ids,
            "assigned_thesis_count": len(assigned_thesis_ids),
            "created_task_count": len(created_task_ids),
            "skipped": skipped,
        },
    )


@router.post("/review-tasks/{task_id}/replace", response_model=MessageResponse)
def replace_review_task(
    task_id: int,
    request: Request,
    payload: ReplaceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    max_per_department = request.app.state.settings.max_reviewers_per_department
    task = db.get(ReviewTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="ReviewTask not found.")
    if task.status not in (
        ReviewTaskStatus.ASSIGNED,
        ReviewTaskStatus.DRAFTING,
        ReviewTaskStatus.RETURNED,
    ):
        raise HTTPException(status_code=400, detail="Current status does not allow replacement.")

    thesis = db.get(Thesis, task.thesis_id)
    if thesis and thesis.advisor_id and payload.new_reviewer_id == thesis.advisor_id:
        raise HTTPException(status_code=400, detail="New reviewer conflicts with advisor.")
    reviewer = db.get(User, payload.new_reviewer_id)
    if reviewer is None:
        reviewer = User(
            id=payload.new_reviewer_id,
            role=UserRole.REVIEWER,
            name=f"reviewer-{payload.new_reviewer_id}",
            department=None,
        )
        db.add(reviewer)
        db.flush()
    elif reviewer.role != UserRole.REVIEWER:
        raise HTTPException(status_code=400, detail="New reviewer is not a reviewer.")

    _validate_department_quota(
        db=db,
        thesis_id=task.thesis_id,
        new_reviewer_ids={payload.new_reviewer_id},
        max_per_department=max_per_department,
        exclude_task_id=task.id,
    )

    old_reviewer_id = task.reviewer_id
    task.reviewer_id = payload.new_reviewer_id
    task.status = ReviewTaskStatus.ASSIGNED
    task.return_reason = None
    write_audit_log(
        db,
        user.id,
        "review_task_replace",
        "review_task",
        str(task.id),
        payload={
            "old_reviewer_id": old_reviewer_id,
            "new_reviewer_id": payload.new_reviewer_id,
            "reason": payload.reason,
        },
    )
    db.commit()
    return MessageResponse(message="replaced")


@router.post("/review-tasks/{task_id}/cancel", response_model=MessageResponse)
def cancel_review_task(
    task_id: int,
    payload: CancelRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    task = db.get(ReviewTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="ReviewTask not found.")
    if task.status in (ReviewTaskStatus.SUBMITTED, ReviewTaskStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Submitted/cancelled task cannot be canceled.")
    task.status = ReviewTaskStatus.CANCELLED
    task.cancelled_reason = payload.reason
    write_audit_log(
        db,
        user.id,
        "review_task_cancel",
        "review_task",
        str(task.id),
        payload={"reason": payload.reason},
    )
    refresh_thesis_status_from_tasks(db, task.thesis_id)
    db.commit()
    return MessageResponse(message="cancelled")


@router.post("/review-tasks/{task_id}/return", response_model=MessageResponse)
def return_review_task(
    task_id: int,
    payload: ReturnRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    task = db.get(ReviewTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="ReviewTask not found.")
    if task.status != ReviewTaskStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail="Only submitted task can be returned.")

    form = db.scalar(select(ReviewForm).where(ReviewForm.task_id == task.id))
    if form:
        snapshot = {
            "score": form.score,
            "grade": form.grade,
            "allow_defense": form.allow_defense.value if form.allow_defense else None,
            "comments": form.comments,
            "internal_comments": form.internal_comments,
            "is_final": form.is_final,
            "revision_no": form.revision_no,
            "updated_at": form.updated_at.isoformat(),
        }
        history = ReviewFormHistory(
            task_id=task.id,
            revision_no=form.revision_no,
            snapshot=json.dumps(snapshot, ensure_ascii=False),
        )
        db.add(history)
        form.revision_no += 1
        form.is_final = False

    task.status = ReviewTaskStatus.RETURNED
    task.return_reason = payload.reason
    write_audit_log(
        db,
        user.id,
        "review_task_return",
        "review_task",
        str(task.id),
        payload={"reason": payload.reason},
    )
    refresh_thesis_status_from_tasks(db, task.thesis_id)
    db.commit()
    return MessageResponse(message="returned_for_rework")


@router.get("/review-progress")
def review_progress(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    theses = db.scalars(select(Thesis).order_by(Thesis.id.asc())).all()
    rows = []
    for thesis in theses:
        total = db.scalar(
            select(func.count(ReviewTask.id)).where(
                ReviewTask.thesis_id == thesis.id,
                ReviewTask.status != ReviewTaskStatus.CANCELLED,
            )
        ) or 0
        submitted = db.scalar(
            select(func.count(ReviewTask.id)).where(
                ReviewTask.thesis_id == thesis.id,
                ReviewTask.status == ReviewTaskStatus.SUBMITTED,
            )
        ) or 0
        cancelled = db.scalar(
            select(func.count(ReviewTask.id)).where(
                ReviewTask.thesis_id == thesis.id,
                ReviewTask.status == ReviewTaskStatus.CANCELLED,
            )
        ) or 0
        completion = 0 if total == 0 else int((submitted / total) * 100)
        rows.append(
            {
                "thesis_id": thesis.id,
                "thesis_status": thesis.status.value,
                "total_active_tasks": total,
                "submitted_tasks": submitted,
                "cancelled_tasks": cancelled,
                "completion_percent": completion,
            }
        )
    return {"items": rows, "generated_at": datetime.utcnow().isoformat()}
