from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.session import EventSession
from app.schemas.session import SessionCreate, SessionUpdate


def get_session(db: Session, session_id: int) -> Optional[EventSession]:
    return db.get(EventSession, session_id)


def list_sessions(db: Session, event_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> List[EventSession]:
    stmt = select(EventSession)
    if event_id is not None:
        stmt = stmt.where(EventSession.event_id == event_id)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def create_session(db: Session, data: SessionCreate) -> EventSession:
    row = EventSession(event_id=data.event_id, sessiontime=data.sessiontime, capacity=data.capacity)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_session(db: Session, session_id: int, data: SessionUpdate) -> Optional[EventSession]:
    row = get_session(db, session_id)
    if not row:
        return None
    if data.sessiontime is not None:
        row.sessiontime = data.sessiontime
    if data.capacity is not None:
        row.capacity = data.capacity
    db.commit()
    db.refresh(row)
    return row


def delete_session(db: Session, session_id: int) -> Optional[EventSession]:
    row = get_session(db, session_id)
    if not row:
        return None
    db.delete(row)
    db.commit()
    return row


