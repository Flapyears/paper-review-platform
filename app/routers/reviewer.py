from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import (
    DefenseDecision,
    FileRecord,
    ReviewForm,
    ReviewTask,
    ReviewTaskStatus,
    Thesis,
    ThesisVersion,
    User,
    UserRole,
)
from app.schemas import MessageResponse, ReviewFormDraftRequest
from app.services.audit import write_audit_log
from app.services.state_machine import refresh_thesis_status_from_tasks

router = APIRouter(prefix="/api/reviewer", tags=["reviewer"])


@router.get("/tasks")
def list_my_tasks(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REVIEWER)),
):
    tasks = db.scalars(
        select(ReviewTask)
        .where(ReviewTask.reviewer_id == user.id)
        .order_by(ReviewTask.created_at.desc())
    ).all()
    items = []
    for task in tasks:
        thesis = db.get(Thesis, task.thesis_id)
        items.append(
            {
                "task_id": task.id,
                "thesis_id": task.thesis_id,
                "thesis_title": thesis.title if thesis else None,
                "status": task.status.value,
                "due_at": task.due_at.isoformat() if task.due_at else None,
                "is_overdue": bool(task.due_at and task.due_at < datetime.utcnow()),
            }
        )
    return {"items": items}


@router.get("/tasks/{task_id}")
def task_detail(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REVIEWER)),
):
    task = db.get(ReviewTask, task_id)
    if not task or task.reviewer_id != user.id:
        raise HTTPException(status_code=404, detail="ReviewTask not found.")
    form = db.scalar(select(ReviewForm).where(ReviewForm.task_id == task.id))
    thesis = db.get(Thesis, task.thesis_id)
    version = db.get(ThesisVersion, task.version_id)
    return {
        "task": {
            "id": task.id,
            "status": task.status.value,
            "thesis_id": task.thesis_id,
            "thesis_title": thesis.title if thesis else None,
            "version_id": task.version_id,
            "version_no": version.version_no if version else None,
            "download_count": task.download_count,
            "last_downloaded_at": task.last_downloaded_at.isoformat()
            if task.last_downloaded_at
            else None,
            "return_reason": task.return_reason,
        },
        "form": _serialize_form(form),
    }


@router.get("/tasks/{task_id}/download")
def download_task_file(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REVIEWER)),
):
    task = db.get(ReviewTask, task_id)
    if not task or task.reviewer_id != user.id:
        raise HTTPException(status_code=404, detail="ReviewTask not found.")
    version = db.get(ThesisVersion, task.version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found.")
    file_record = db.get(FileRecord, version.file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail="File not found.")
    file_path = Path(file_record.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File is missing on storage.")

    task.download_count += 1
    task.last_downloaded_at = datetime.utcnow()
    write_audit_log(
        db,
        user.id,
        "review_task_download",
        "review_task",
        str(task.id),
        payload={"file_id": file_record.id},
    )
    db.commit()
    return FileResponse(
        path=str(file_path),
        filename=file_record.original_name,
        media_type=file_record.mime or "application/octet-stream",
    )


@router.put("/tasks/{task_id}/form", response_model=MessageResponse)
def save_review_form_draft(
    task_id: int,
    payload: ReviewFormDraftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REVIEWER)),
):
    task = db.get(ReviewTask, task_id)
    if not task or task.reviewer_id != user.id:
        raise HTTPException(status_code=404, detail="ReviewTask not found.")
    if task.status in (ReviewTaskStatus.SUBMITTED, ReviewTaskStatus.CANCELLED):
        raise HTTPException(status_code=400, detail="Current task cannot be edited.")

    form = db.scalar(select(ReviewForm).where(ReviewForm.task_id == task.id))
    if form is None:
        form = ReviewForm(task_id=task.id)
        db.add(form)

    form.score = payload.score
    form.grade = payload.grade
    form.comments = payload.comments
    form.internal_comments = payload.internal_comments
    if payload.allow_defense is None:
        form.allow_defense = None
    else:
        try:
            form.allow_defense = DefenseDecision(payload.allow_defense)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid allow_defense value.") from exc
    form.is_final = False
    if task.status in (ReviewTaskStatus.ASSIGNED, ReviewTaskStatus.RETURNED):
        task.status = ReviewTaskStatus.DRAFTING
    write_audit_log(db, user.id, "review_form_draft_save", "review_task", str(task.id))
    db.commit()
    return MessageResponse(message="draft_saved")


@router.post("/tasks/{task_id}/submit", response_model=MessageResponse)
def submit_review_form(
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.REVIEWER)),
):
    task = db.get(ReviewTask, task_id)
    if not task or task.reviewer_id != user.id:
        raise HTTPException(status_code=404, detail="ReviewTask not found.")
    if task.status == ReviewTaskStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cancelled task cannot be submitted.")

    form = db.scalar(select(ReviewForm).where(ReviewForm.task_id == task.id))
    if not form:
        raise HTTPException(status_code=400, detail="Review form not found.")
    if form.score is None or form.grade is None or form.allow_defense is None or not form.comments:
        raise HTTPException(status_code=400, detail="Review form is incomplete.")

    form.is_final = True
    task.status = ReviewTaskStatus.SUBMITTED
    task.return_reason = None
    write_audit_log(db, user.id, "review_form_submit", "review_task", str(task.id))
    refresh_thesis_status_from_tasks(db, task.thesis_id)
    db.commit()
    return MessageResponse(message="submitted")


def _serialize_form(form: ReviewForm | None) -> dict | None:
    if form is None:
        return None
    return {
        "score": form.score,
        "grade": form.grade,
        "allow_defense": form.allow_defense.value if form.allow_defense else None,
        "comments": form.comments,
        "internal_comments": form.internal_comments,
        "is_final": form.is_final,
        "revision_no": form.revision_no,
        "updated_at": form.updated_at.isoformat(),
    }
