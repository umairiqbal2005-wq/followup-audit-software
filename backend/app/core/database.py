from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def _create_engine():
    if settings.db_backend.lower() == "oracle":
        from app.core.oracle import (
            build_oracle_engine_kwargs,
            session_harden_sql,
            validate_oracle_identifier,
        )

        # Fail fast on bad schema/edition identifiers before connecting
        validate_oracle_identifier(settings.oracle_schema)
        if settings.oracle_edition:
            validate_oracle_identifier(settings.oracle_edition)

        eng = create_engine(settings.database_url, **build_oracle_engine_kwargs(settings))

        @event.listens_for(eng, "connect")
        def _oracle_on_connect(dbapi_connection, connection_record):  # noqa: ARG001
            cursor = dbapi_connection.cursor()
            try:
                for stmt in session_harden_sql(settings):
                    cursor.execute(stmt)
            finally:
                cursor.close()

        return eng

    eng = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(eng, "connect")
    def _sqlite_on_connect(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ping_database(db: Session) -> bool:
    db.execute(text("SELECT 1 FROM DUAL" if settings.db_backend.lower() == "oracle" else "SELECT 1"))
    return True


def next_observation_sequence_value(db: Session) -> int | None:
    """Return OBS_NUMBER_SEQ.NEXTVAL on Oracle; None on other backends."""
    if settings.db_backend.lower() != "oracle":
        return None
    return db.execute(text("SELECT obs_number_seq.NEXTVAL FROM dual")).scalar()
