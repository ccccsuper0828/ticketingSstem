from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.enums import RefundStatus


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    amount = Column(Integer, nullable=False, default=0)
    reason = Column(Text, nullable=True)
    status = Column(SAEnum(RefundStatus, name="refund_status"), nullable=False, default=RefundStatus.requested)
    refundtime = Column("refundtime", DateTime, nullable=True)
    reviewed_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


