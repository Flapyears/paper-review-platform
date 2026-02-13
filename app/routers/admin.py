from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException
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
    payload: AssignRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
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
                reviewer = User(id=reviewer_id, role=UserRole.REVIEWER, name=f"reviewer-{reviewer_id}")
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
    payload: ReplaceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
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
        )
        db.add(reviewer)
        db.flush()
    elif reviewer.role != UserRole.REVIEWER:
        raise HTTPException(status_code=400, detail="New reviewer is not a reviewer.")

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
