from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import (
    ReviewForm,
    ReviewFormHistory,
    ReviewTask,
    ReviewTaskStatus,
    Thesis,
    ThesisStatus,
    User,
    UserRole,
)
from app.schemas import (
    AssignRequest,
    CancelRequest,
    MessageResponse,
    ReplaceRequest,
    ReturnRequest,
)
from app.services.audit import write_audit_log
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
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    thesis = db.get(Thesis, thesis_id) if thesis_id else None
    if thesis_id and thesis is None:
        raise HTTPException(status_code=404, detail="Thesis not found.")
    max_per_department = request.app.state.settings.max_reviewers_per_department

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
                "assigned_count": assigned_count or 0,
                "created_at": thesis.created_at.isoformat(),
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
    max_per_department = request.app.state.settings.max_reviewers_per_department
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
