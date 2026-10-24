from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str, poolclass=None) -> Engine:
    connect_args = {}
    if database_url.startswith("sqlite"):
        # FastAPI may run a request on a different thread than the one that opened the connection.
        connect_args["check_same_thread"] = False

    engine_kwargs = {"connect_args": connect_args}
    if poolclass is not None:
        engine_kwargs["poolclass"] = poolclass
    engine = create_engine(database_url, **engine_kwargs)

    if database_url.startswith("sqlite"):
        # SQLite ignores foreign keys unless this pragma is set on every connection.
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
