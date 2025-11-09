from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, LargeBinary, String, func

from app.db.base import Base
from app.models.enums import TicketStatus


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_type_id = Column(Integer, nullable=False)
    session_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    seat_id = Column(Integer, nullable=True)
    status = Column(SAEnum(TicketStatus, name="ticket_status"), nullable=False, default=TicketStatus.pending)
    qr_code = Column(LargeBinary, nullable=False)
    purchase_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


