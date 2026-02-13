from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ReviewTask, ReviewTaskStatus, Thesis, ThesisStatus


def refresh_thesis_status_from_tasks(db: Session, thesis_id: int) -> None:
    thesis = db.get(Thesis, thesis_id)
    if thesis is None:
        return

    total_active = db.scalar(
        select(func.count(ReviewTask.id)).where(
            ReviewTask.thesis_id == thesis_id,
            ReviewTask.status != ReviewTaskStatus.CANCELLED,
        )
    )
    if not total_active:
        if thesis.status in (ThesisStatus.REVIEWING, ThesisStatus.REVIEW_DONE):
            thesis.status = ThesisStatus.SUBMITTED
        return

    submitted_active = db.scalar(
        select(func.count(ReviewTask.id)).where(
            ReviewTask.thesis_id == thesis_id,
            ReviewTask.status == ReviewTaskStatus.SUBMITTED,
        )
    )
    if submitted_active == total_active:
        thesis.status = ThesisStatus.REVIEW_DONE
    else:
        thesis.status = ThesisStatus.REVIEWING

