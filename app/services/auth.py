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
    """
    仅兜底创建管理员账号，避免每次启动自动回灌学生/教师演示账号。
    默认管理员首次登录后必须修改密码，后续修改不会在启动时被覆盖。
    """

    defaults = [
        {
            "role": UserRole.ADMIN,
            "name": "管理员",
            "username": "admin",
            "password": "admin",
            "department": None,
            "must_change_password": True,
        },
    ]
    changed = False
    for item in defaults:
        user = db.scalar(select(User).where(User.role == item["role"]).order_by(User.id.asc()))
        if user is None:
            user = User(
                role=item["role"],
                name=item["name"],
                department=item["department"],
            )
            db.add(user)
            db.flush()
            changed = True
        elif user.name != item["name"] or user.department != item["department"]:
            user.name = item["name"]
            user.department = item["department"]
            changed = True
        credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == user.id))
        if credential is None:
            credential = AuthCredential(
                user_id=user.id,
                username=item["username"],
                password_hash=hash_password(item["password"]),
                is_active=True,
                must_change_password=item["must_change_password"],
            )
            db.add(credential)
            changed = True
    if changed:
        db.commit()


def seed_demo_accounts(db: Session) -> None:
    """
    仅供测试或显式演示环境使用，保留旧的固定账号编号，避免影响现有用例。
    """

    defaults = [
        {
            "user_id": 1,
            "role": UserRole.STUDENT,
            "name": "student-1",
            "username": "student1",
            "password": "student123",
            "department": None,
        },
        {
            "user_id": 2,
            "role": UserRole.ADMIN,
            "name": "admin-2",
            "username": "admin1",
            "password": "admin123",
            "department": None,
        },
        {
            "user_id": 3,
            "role": UserRole.REVIEWER,
            "name": "reviewer-3",
            "username": "reviewer1",
            "password": "reviewer123",
            "department": "计算机系",
        },
        {
            "user_id": 4,
            "role": UserRole.REVIEWER,
            "name": "reviewer-4",
            "username": "reviewer2",
            "password": "reviewer123",
            "department": "软件系",
        },
        {
            "user_id": 5,
            "role": UserRole.REVIEWER,
            "name": "reviewer-5",
            "username": "reviewer3",
            "password": "reviewer123",
            "department": "计算机系",
        },
    ]
    changed = False
    for item in defaults:
        user = db.get(User, item["user_id"])
        if user is None:
            user = User(
                id=item["user_id"],
                role=item["role"],
                name=item["name"],
                department=item["department"],
            )
            db.add(user)
            db.flush()
            changed = True
        elif user.role != item["role"] or user.name != item["name"] or user.department != item["department"]:
            user.role = item["role"]
            user.name = item["name"]
            user.department = item["department"]
            changed = True

        credential = db.scalar(select(AuthCredential).where(AuthCredential.user_id == user.id))
        if credential is None:
            credential = AuthCredential(
                user_id=user.id,
                username=item["username"],
                password_hash=hash_password(item["password"]),
                is_active=True,
                must_change_password=False,
            )
            db.add(credential)
            changed = True
    if changed:
        db.commit()
