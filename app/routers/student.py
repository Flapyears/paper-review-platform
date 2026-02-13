from datetime import datetime
from hashlib import sha256
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_roles
from app.models import (
    FileRecord,
    Thesis,
    ThesisStatus,
    ThesisVersion,
    User,
    UserRole,
)
from app.schemas import MessageResponse, ThesisCreateRequest, ThesisUpdateRequest
from app.services.audit import write_audit_log

router = APIRouter(prefix="/api/thesis", tags=["student"])


def _get_my_thesis(db: Session, student_id: int) -> Thesis | None:
    return db.scalar(select(Thesis).where(Thesis.student_id == student_id))


@router.get("/my")
def get_my_thesis(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.STUDENT)),
):
    thesis = _get_my_thesis(db, user.id)
    if thesis is None:
        return {"thesis": None}
    return {"thesis": _serialize_thesis(thesis)}


@router.post("/my", response_model=MessageResponse)
def create_my_thesis(
    payload: ThesisCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.STUDENT)),
):
    existing = _get_my_thesis(db, user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Student thesis already exists.")
    if payload.advisor_id is not None:
        advisor = db.get(User, payload.advisor_id)
        if advisor is None:
            advisor = User(
                id=payload.advisor_id,
                role=UserRole.REVIEWER,
                name=f"advisor-{payload.advisor_id}",
            )
            db.add(advisor)
            db.flush()
    thesis = Thesis(title=payload.title.strip(), student_id=user.id, advisor_id=payload.advisor_id)
    db.add(thesis)
    db.flush()
    write_audit_log(db, user.id, "thesis_create", "thesis", str(thesis.id))
    db.commit()
    return MessageResponse(message="created", data={"thesis_id": thesis.id})


@router.put("/{thesis_id}", response_model=MessageResponse)
def update_my_thesis(
    thesis_id: int,
    payload: ThesisUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.STUDENT)),
):
    thesis = db.get(Thesis, thesis_id)
    if not thesis or thesis.student_id != user.id:
        raise HTTPException(status_code=404, detail="Thesis not found.")
    if thesis.status != ThesisStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT thesis can be edited.")
    thesis.title = payload.title.strip()
    write_audit_log(db, user.id, "thesis_update", "thesis", str(thesis.id))
    db.commit()
    return MessageResponse(message="updated")


@router.post("/{thesis_id}/upload-final", response_model=MessageResponse)
async def upload_final(
    thesis_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.STUDENT)),
):
    thesis = db.get(Thesis, thesis_id)
    if not thesis or thesis.student_id != user.id:
        raise HTTPException(status_code=404, detail="Thesis not found.")
    if thesis.status != ThesisStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Current thesis status does not allow upload.")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    ext = Path(file.filename).suffix.lower()
    settings = request.app.state.settings
    if ext not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail="File extension not allowed.")

    storage_dir = Path(settings.storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_filename = f"{uuid.uuid4().hex}{ext}"
    storage_path = storage_dir / storage_filename

    hasher = sha256()
    size = 0
    chunk_size = 1024 * 1024
    try:
        with storage_path.open("wb") as output:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.max_upload_size:
                    raise HTTPException(status_code=400, detail="File exceeds max upload size.")
                output.write(chunk)
                hasher.update(chunk)
    except Exception:
        if storage_path.exists():
            storage_path.unlink()
        raise

    file_record = FileRecord(
        storage_path=str(storage_path.resolve()),
        original_name=file.filename,
        sha256=hasher.hexdigest(),
        mime=file.content_type,
        size=size,
        uploaded_by=user.id,
    )
    db.add(file_record)
    db.flush()

    version = ThesisVersion(thesis_id=thesis.id, file_id=file_record.id, stage="final")
    db.add(version)
    db.flush()

    thesis.current_version_id = version.id
    thesis.return_reason = None
    write_audit_log(
        db,
        user.id,
        "thesis_upload_final",
        "thesis",
        str(thesis.id),
        payload={"version_id": version.id, "file_id": file_record.id},
    )
    db.commit()
    return MessageResponse(message="uploaded", data={"version_id": version.id, "file_id": file_record.id})


@router.post("/{thesis_id}/submit-final", response_model=MessageResponse)
def submit_final(
    thesis_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.STUDENT)),
):
    thesis = db.get(Thesis, thesis_id)
    if not thesis or thesis.student_id != user.id:
        raise HTTPException(status_code=404, detail="Thesis not found.")
    if thesis.status != ThesisStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT thesis can be submitted.")
    if thesis.current_version_id is None:
        raise HTTPException(status_code=400, detail="No current version to submit.")

    version = db.get(ThesisVersion, thesis.current_version_id)
    if version is None:
        raise HTTPException(status_code=400, detail="Current version missing.")
    thesis.status = ThesisStatus.SUBMITTED
    version.locked_for_review = True
    version.submitted_at = datetime.utcnow()
    write_audit_log(
        db,
        user.id,
        "thesis_submit_final",
        "thesis",
        str(thesis.id),
        payload={"version_id": version.id},
    )
    db.commit()
    return MessageResponse(message="submitted", data={"thesis_status": thesis.status.value})


def _serialize_thesis(thesis: Thesis) -> dict:
    return {
        "id": thesis.id,
        "title": thesis.title,
        "status": thesis.status.value,
        "current_version_id": thesis.current_version_id,
        "return_reason": thesis.return_reason,
        "advisor_id": thesis.advisor_id,
    }
