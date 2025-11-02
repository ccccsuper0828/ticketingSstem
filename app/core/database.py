from typing import Generator

from sqlalchemy.orm import Session

# Re-export database primitives from the db package to maintain backward compatibility.
from app.db.base import Base  # noqa: F401
from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


