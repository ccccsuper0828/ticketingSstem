from typing import List, Optional
from uuid import uuid4

from app.models.enums import EventStatus
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.event import Event
from app.schemas.event import EventCreate, EventUpdate

def get_event(db: Session, event_id: int) -> Optional[Event]:
    return db.get(Event, event_id)

def list_events(db: Session, skip: int = 0, limit: int = 10) -> List[Event]:
    stmt = select(Event).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())

def create_event(db: Session, data: EventCreate, cover_image_url: Optional[str] = None) -> Event:
    db_event = Event(
        name=data.name,
        description=data.description,
        start_time=data.start_time,
        end_time=data.end_time,
        location=data.location,
        status=data.status or EventStatus.draft.value,
        cover_image=cover_image_url,
        created_by=data.created_by,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def update_event(db: Session, event_id: int, data: EventUpdate) -> Optional[Event]:
    db_event = get_event(db, event_id)
    if not db_event:
        return None
    if data.name is not None:
        db_event.name = data.name
    if data.description is not None:
        db_event.description = data.description
    if data.start_time is not None:
        db_event.start_time = data.start_time
    if data.end_time is not None:
        db_event.end_time = data.end_time
    if data.status is not None:
        db_event.status = data.status
    db.commit()
    db.refresh(db_event)
    return db_event

def delete_event(db: Session, event_id: int) -> Optional[Event]:
    db_event = get_event(db, event_id)
    if not db_event:
        return None
    db.delete(db_event)
    db.commit()
    return db_event     

def publish_event(db: Session, event_id: int)  -> Optional[Event]:
    db_event = get_event(db, event_id)
    if not db_event:
        return None
    db_event.status = EventStatus.published
    db.commit()
    db.refresh(db_event)
    return db_event