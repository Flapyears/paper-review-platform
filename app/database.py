from collections.abc import Generator

from sqlalchemy import create_engine, event
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


def get_db_session(session_local) -> Generator[Session, None, None]:  # noqa: ANN001
    db = session_local()
    try:
        yield db
    finally:
        db.close()
