import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit_log(
    db: Session,
    actor_id: int,
    action: str,
    target_type: str,
    target_id: str,
    payload: dict[str, Any] | None = None,
) -> None:
    record = AuditLog(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        payload=json.dumps(payload, ensure_ascii=False) if payload else None,
    )
    db.add(record)

