from datetime import datetime, timedelta
import hashlib
import secrets

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AuthCredential, AuthSession, User, UserRole


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, digest_hex = hashed.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200000)
    return secrets.compare_digest(digest.hex(), digest_hex)


def create_session(db: Session, user_id: int, hours: int = 24) -> AuthSession:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=hours)
    session = AuthSession(user_id=user_id, token=token, expires_at=expires_at)
    db.add(session)
    db.flush()
    return session


def remove_session(db: Session, token: str) -> None:
    db.execute(delete(AuthSession).where(AuthSession.token == token))


def get_user_by_token(db: Session, token: str) -> User | None:
    session = db.scalar(
        select(AuthSession).where(AuthSession.token == token, AuthSession.expires_at > datetime.utcnow())
    )
    if not session:
        return None
    return db.get(User, session.user_id)


def seed_default_accounts(db: Session) -> None:
    defaults = [
        {"user_id": 1, "role": UserRole.STUDENT, "name": "student-1", "username": "student1", "password": "student123"},
        {"user_id": 2, "role": UserRole.ADMIN, "name": "admin-2", "username": "admin1", "password": "admin123"},
        {"user_id": 3, "role": UserRole.REVIEWER, "name": "reviewer-3", "username": "reviewer1", "password": "reviewer123"},
        {"user_id": 4, "role": UserRole.REVIEWER, "name": "reviewer-4", "username": "reviewer2", "password": "reviewer123"},
    ]
    changed = False
    for item in defaults:
        user = db.get(User, item["user_id"])
        if user is None:
            user = User(id=item["user_id"], role=item["role"], name=item["name"])
            db.add(user)
            db.flush()
            changed = True
        credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == user.id))
        if credential is None:
            credential = AuthCredential(
                user_id=user.id,
                username=item["username"],
                password_hash=hash_password(item["password"]),
                is_active=True,
            )
            db.add(credential)
            changed = True
    if changed:
        db.commit()

