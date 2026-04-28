from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def create_engine_and_session(database_url: str) -> tuple:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args, future=True)
    if database_url.startswith("sqlite"):
        event.listen(engine, "connect", _set_sqlite_pragma)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=True, class_=Session)


def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001, ARG001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_tables(engine) -> None:  # noqa: ANN001
    Base.metadata.create_all(bind=engine)


def run_compat_migrations(engine) -> None:  # noqa: ANN001
    """Apply lightweight additive migrations for local SQLite deployments."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    auth_columns = (
        {col["name"] for col in inspector.get_columns("auth_credentials")}
        if "auth_credentials" in inspector.get_table_names()
        else set()
    )
    statements: list[str] = []
    if "department" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN department VARCHAR(64)")
    if "student_no" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN student_no VARCHAR(64)")
    statements.append(
        "CREATE INDEX IF NOT EXISTS ix_users_department ON users (department)"
    )
    statements.append(
        "CREATE INDEX IF NOT EXISTS ix_users_student_no ON users (student_no)"
    )
    if "must_change_password" not in auth_columns:
        statements.append(
            "ALTER TABLE auth_credentials ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0"
        )
    if "thesis_versions" in inspector.get_table_names():
        version_columns = {col["name"] for col in inspector.get_columns("thesis_versions")}
        if "version_no" not in version_columns:
            statements.append("ALTER TABLE thesis_versions ADD COLUMN version_no INTEGER")
            # Backfill per-thesis version number in creation order.
            statements.append(
                """
                WITH ranked AS (
                  SELECT id,
                         ROW_NUMBER() OVER (PARTITION BY thesis_id ORDER BY created_at ASC, id ASC) AS rn
                  FROM thesis_versions
                )
                UPDATE thesis_versions
                SET version_no = (SELECT rn FROM ranked WHERE ranked.id = thesis_versions.id)
                WHERE version_no IS NULL
                """
            )
            statements.append("UPDATE thesis_versions SET version_no = 1 WHERE version_no IS NULL")
        statements.append(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_thesis_versions_thesis_version_no "
            "ON thesis_versions (thesis_id, version_no)"
        )

    if not statements:
        return
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def get_db_session(session_local) -> Generator[Session, None, None]:  # noqa: ANN001
    db = session_local()
    try:
        yield db
    finally:
        db.close()
