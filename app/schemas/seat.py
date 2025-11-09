from typing import List, Optional
from pydantic import BaseModel


class SeatStats(BaseModel):
    total: int
    available: int
    soldCount: int
    lockedCount: int


class SeatStateRead(BaseModel):
    sessionId: int
    ticketTypeId: int
    sold: List[int]
    locked: List[int]
    stats: SeatStats


class SeatItem(BaseModel):
    id: int
    section: str | None = None
    row: str | None = None
    number: str | None = None
    status: str  # available|sold|locked


class SeatRowGroup(BaseModel):
    row: str | None = None
    seats: List[SeatItem]


class SeatMapRead(BaseModel):
    eventId: int
    sessionId: int | None = None
    ticketTypeId: int | None = None
    rows: List[SeatRowGroup]
    stats: SeatStats


