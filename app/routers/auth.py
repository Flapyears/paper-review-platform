from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import AuthCredential, User
from app.schemas import LoginRequest, MessageResponse
from app.services.auth import create_session, remove_session, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=MessageResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    credential = db.scalar(
        select(AuthCredential).where(AuthCredential.username == payload.username, AuthCredential.is_active)
    )
    if credential is None or not verify_password(payload.password, credential.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    user = db.get(User, credential.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    session = create_session(db, user.id)
    db.commit()
    return MessageResponse(
        message="login_success",
        data={
            "token": session.token,
            "user": {"id": user.id, "name": user.name, "role": user.role.value},
        },
    )


@router.get("/me", response_model=MessageResponse)
def me(user: User = Depends(get_current_user)):
    return MessageResponse(
        message="ok",
        data={"user": {"id": user.id, "name": user.name, "role": user.role.value}},
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        remove_session(db, token)
        db.commit()
    return MessageResponse(message="logout_success", data={"user_id": user.id})

