from typing import Generator

from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

# Re-export database primitives from the db package to maintain backward compatibility.
from app.db.base import Base  # noqa: F401
from app.db.session import SessionLocal

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


