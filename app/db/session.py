from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.database_echo,
    future=True,
    pool_size=settings.db_connection_limit,
    max_overflow=0,  # hard cap at connection_limit
    pool_timeout=settings.db_acquire_timeout_seconds,
    connect_args={"connect_timeout": settings.db_timeout_seconds},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


