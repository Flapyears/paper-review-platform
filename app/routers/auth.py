from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import AuthCredential, User
from app.schemas import LoginRequest, MessageResponse, PasswordChangeRequest
from app.services.auth import create_session, hash_password, remove_session, verify_password

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
            "user": {
                "id": user.id,
                "name": user.name,
                "role": user.role.value,
                "must_change_password": credential.must_change_password,
            },
        },
    )


@router.get("/me", response_model=MessageResponse)
def me(user: User = Depends(get_current_user)):
    credential = getattr(user, "_auth_credential", None)
    return MessageResponse(
        message="ok",
        data={
            "user": {
                "id": user.id,
                "name": user.name,
                "role": user.role.value,
                "must_change_password": bool(credential.must_change_password) if credential else False,
            }
        },
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


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == user.id))
    if credential is None:
        raise HTTPException(status_code=404, detail="Credential not found.")
    if not verify_password(payload.old_password, credential.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different.")

    credential.password_hash = hash_password(payload.new_password)
    credential.must_change_password = False
    db.commit()
    return MessageResponse(message="password_changed", data={"must_change_password": False})

