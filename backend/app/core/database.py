from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.db_backend.lower() == "sqlite" else {}
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=20 if settings.db_backend.lower() == "oracle" else 5,
    max_overflow=40 if settings.db_backend.lower() == "oracle" else 10,
    connect_args=connect_args,
)

if settings.db_backend.lower() == "sqlite":

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
