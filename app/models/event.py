from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, String, Text, func

from app.db.base import Base
from app.models.enums import EventStatus

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    location = Column(String(255), nullable=True)
    cover_image = Column(String(512), nullable=True)
    status = Column(SAEnum(EventStatus, name="event_status"), nullable=False, default=EventStatus.draft)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)