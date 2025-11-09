from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict


class SessionCreate(BaseModel):
    event_id: int
    sessiontime: datetime
    capacity: int = 0


class SessionRead(BaseModel):
    id: int
    event_id: int
    sessiontime: datetime
    capacity: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionUpdate(BaseModel):
    sessiontime: Optional[datetime] = None
    capacity: Optional[int] = None


