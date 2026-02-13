from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models import User, UserRole


def get_db(request: Request):
    yield from get_db_session(request.app.state.session_local)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    x_user_id: int | None = Header(default=None),
    x_role: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
) -> User:
    if x_user_id is None or not x_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id or X-Role header.",
        )
    try:
        role = UserRole(x_role.lower())
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid role header.") from exc

    user = db.get(User, x_user_id)
    if user is None:
        user = User(id=x_user_id, role=role, name=x_user_name or f"user-{x_user_id}")
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.role != role:
        raise HTTPException(status_code=403, detail="Role mismatch for this user.")
    return user


def require_roles(*roles: UserRole) -> Callable:
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden.")
        return user

    return _checker

