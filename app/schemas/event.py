from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict


class EventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    status: str = "draft"
    created_by: Optional[int] = None

class EventRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    cover_image: Optional[str] = None
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    status: Optional[str] = None

# Backwards compatibility alias for existing imports
eventCreate = EventCreate