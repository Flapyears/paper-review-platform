from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import FileRecord, ReviewTask, Thesis, ThesisVersion, User, UserRole

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    file_record = db.get(FileRecord, file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail="File not found.")

    if user.role == UserRole.ADMIN:
        allowed = True
    elif user.role == UserRole.STUDENT:
        allowed = db.scalar(
            select(ThesisVersion.id)
            .join(Thesis, Thesis.id == ThesisVersion.thesis_id)
            .where(Thesis.student_id == user.id, ThesisVersion.file_id == file_id)
            .limit(1)
        )
    else:
        allowed = db.scalar(
            select(ReviewTask.id)
            .join(ThesisVersion, ThesisVersion.id == ReviewTask.version_id)
            .where(ReviewTask.reviewer_id == user.id, ThesisVersion.file_id == file_id)
            .limit(1)
        )
    if not allowed:
        raise HTTPException(status_code=403, detail="Forbidden.")

    path = Path(file_record.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File is missing on storage.")
    return FileResponse(
        path=str(path),
        filename=file_record.original_name,
        media_type=file_record.mime or "application/octet-stream",
    )
