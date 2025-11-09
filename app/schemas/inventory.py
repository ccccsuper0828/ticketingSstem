from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict


class InventoryCreate(BaseModel):
    session_id: int
    ticket_type_id: int
    price: int
    total: int


class InventoryUpdate(BaseModel):
    price: Optional[int] = None
    total: Optional[int] = None
    available: Optional[int] = None


class InventoryRead(BaseModel):
    id: int
    session_id: int
    ticket_type_id: int
    price: int
    total: int
    available: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


