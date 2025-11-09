from sqlalchemy import Column, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func

from app.db.base import Base


class EventSession(Base):
    __tablename__ = "event_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, nullable=False)  # FK -> events.id
    sessiontime = Column(DateTime, nullable=False)  # 按给定表结构字段名
    capacity = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


