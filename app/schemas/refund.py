from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict


class RefundRequestCreate(BaseModel):
    reason: Optional[str] = None


class RefundRead(BaseModel):
    id: int
    ticket_id: int
    user_id: int
    amount: int
    status: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


