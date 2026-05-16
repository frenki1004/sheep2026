import logging
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

log = logging.getLogger(__name__)

settings = get_settings()

engine: Engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

_SPATIALITE_CANDIDATES = (
    "mod_spatialite",
    "mod_spatialite.so",
    "/usr/lib/x86_64-linux-gnu/mod_spatialite.so",
    "/opt/homebrew/lib/mod_spatialite.dylib",
    "/usr/local/lib/mod_spatialite.dylib",
)


def _load_spatialite(dbapi_conn, _connection_record) -> None:
    """Attempt to load mod_spatialite. Warn but don't crash if unavailable."""
    candidates = [settings.spatialite_path] if settings.spatialite_path else list(_SPATIALITE_CANDIDATES)
    dbapi_conn.enable_load_extension(True)
    last_err: Exception | None = None
    for cand in candidates:
        if not cand:
            continue
        try:
            dbapi_conn.load_extension(cand)
            dbapi_conn.enable_load_extension(False)
            return
        except Exception as err:  # pragma: no cover — depends on OS
            last_err = err
    dbapi_conn.enable_load_extension(False)
    log.warning(
        "mod_spatialite not loaded (tried %s). Spatial queries will be unavailable. "
        "On Ubuntu: `sudo apt install libsqlite3-mod-spatialite`. Last error: %s",
        candidates,
        last_err,
    )


if settings.database_url.startswith("sqlite"):
    event.listen(engine, "connect", _load_spatialite)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def spatialite_available() -> bool:
    """Return True if mod_spatialite loaded successfully."""
    if not settings.database_url.startswith("sqlite"):
        return True
    with engine.connect() as conn:
        try:
            row = conn.exec_driver_sql("SELECT spatialite_version()").fetchone()
            return row is not None
        except Exception:
            return False
