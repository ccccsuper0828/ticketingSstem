from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class TicketType(Base):
    __tablename__ = "ticket_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Prefer event_id per PDF schema; keep compatibility
    event_id = Column(Integer, nullable=True)
    eventid = Column(Integer, nullable=True)
    name = Column(String(120), nullable=False)
    price = Column(Integer, nullable=False, default=0)  # 用整数价格（单位与 User.credit 对齐）
    totalstock = Column(Integer, nullable=False, default=0)
    availablestock = Column("available_stock", Integer, nullable=False, default=0)
    description = Column(String, nullable=True)
    createdat = Column("createdat", DateTime, server_default=func.now(), nullable=False)
    updatedat = Column("updatedat", DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


