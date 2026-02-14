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
    statements: list[str] = []
    if "department" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN department VARCHAR(64)")
    statements.append(
        "CREATE INDEX IF NOT EXISTS ix_users_department ON users (department)"
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
