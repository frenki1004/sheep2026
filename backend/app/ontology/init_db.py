"""Create all ontology tables. Idempotent; safe to re-run.

Usage:
    uv run python -m app.ontology.init_db
"""
from __future__ import annotations

import logging

from app.db import engine
from app.ontology.models import Base

log = logging.getLogger(__name__)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    log.info("Ontology schema created (or already present).")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    init_db()
    print("Schema OK.")
