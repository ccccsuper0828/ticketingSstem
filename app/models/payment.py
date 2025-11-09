from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.enums import PaymentMethod, PaymentStatus


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    amount = Column(Integer, nullable=False, default=0)  # 与 credit 单位一致（整数）
    paymentmethod = Column("payment_method", SAEnum(PaymentMethod, name="payment_method"), nullable=False, default=PaymentMethod.credit)
    status = Column(SAEnum(PaymentStatus, name="payment_status"), nullable=False, default=PaymentStatus.paid)
    transaction_id = Column(String(128), unique=True, nullable=False)
    payment_time = Column(DateTime, nullable=True)
    createdat = Column("created_at", DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


