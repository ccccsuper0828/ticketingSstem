from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict, field_serializer
import base64


class TicketPurchase(BaseModel):
    session_id: int
    ticket_type_id: int
    seat_id: Optional[int] = None


class TicketCreate(BaseModel):
    ticket_type_id: int
    session_id: int
    user_id: int
    seat_id: Optional[int] = None


class TicketUpdate(BaseModel):
    seat_id: Optional[int] = None
    status: Optional[str] = None


class TicketRead(BaseModel):
    id: int
    ticket_type_id: int
    session_id: int
    user_id: int
    seat_id: Optional[int] = None
    status: str
    qr_code: bytes
    purchase_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("qr_code")
    def serialize_qr_code(self, v: bytes) -> str:
        # Encode PNG bytes as base64 string for JSON transport
        return base64.b64encode(v).decode("ascii")


class TicketListItem(BaseModel):
    id: int
    user_id: int
    session_id: int
    ticket_type_id: int
    seat_id: Optional[int] = None
    status: str
    price: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

