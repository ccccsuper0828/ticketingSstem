from sqlalchemy import Column, Integer, UniqueConstraint
from sqlalchemy.orm import declarative_mixin
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from app.db.base import Base


class TicketInventory(Base):
    __tablename__ = "ticket_inventory"
    __table_args__ = (
        UniqueConstraint("session_id", "ticket_type_id", name="uq_inventory_session_ticket_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, nullable=False)
    ticket_type_id = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False, default=0)  # 单位与 User.credit 一致，整数
    total = Column(Integer, nullable=False, default=0)
    available = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


