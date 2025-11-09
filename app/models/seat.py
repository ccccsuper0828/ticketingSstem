from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.enums import SeatStatus


class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Prefer event_id per PDF schema; keep compatibility with existing data
    event_id = Column(Integer, nullable=True)  # FK -> events.id
    eventid = Column(Integer, nullable=True)  # legacy/compat
    section = Column(String(50), nullable=True)
    row = Column("rowsnumber", String(20), nullable=True)
    number = Column(String(20), nullable=True)
    status = Column(SAEnum(SeatStatus, name="seat_status"), nullable=False, default=SeatStatus.available)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


