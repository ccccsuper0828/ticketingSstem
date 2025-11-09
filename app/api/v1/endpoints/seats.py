from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.db.session import SessionLocal
from app import models
from app.models.ticket import Ticket
from app.models.enums import TicketStatus
from app.models.inventory import TicketInventory
from app.models.session import EventSession
from app.models.seat import Seat
from app.models.enums import SeatStatus
from app.schemas import seat as seat_schemas
from app.schemas.seat import SeatStateRead, SeatStats


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/state", response_model=SeatStateRead)
def get_seat_state(
    session_id: int = Query(..., description="场次 ID"),
    ticket_type_id: int = Query(..., description="票种 ID"),
    lock_ttl_seconds: int = Query(180, ge=0, le=3600, description="将 pending 票视为锁定的时间窗口（秒）"),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    lock_deadline = now - timedelta(seconds=lock_ttl_seconds)

    # Resolve event id for this session to filter seats
    es = db.execute(select(EventSession).where(EventSession.id == session_id)).scalars().first()
    event_id = int(getattr(es, "event_id", 0)) if es else 0

    # 统计库存
    inv = db.execute(
        select(TicketInventory).where(
            TicketInventory.session_id == session_id,
            TicketInventory.ticket_type_id == ticket_type_id,
        )
    ).scalars().first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory not found")

    # 已售座位（active/used 且有 seat_id）
    sold_rows: List[int] = [
        r[0]
        for r in db.execute(
            select(Ticket.seat_id).where(
                Ticket.session_id == session_id,
                Ticket.ticket_type_id == ticket_type_id,
                Ticket.seat_id.isnot(None),
                Ticket.status.in_([TicketStatus.active, TicketStatus.used]),
            )
        ).all()
        if r[0] is not None
    ]

    # 锁定座位： seats 表中 status=locked 且未过期
    locked_rows_seats: List[int] = [
        r[0]
        for r in db.execute(
            select(Seat.id).where(
                (Seat.event_id == event_id),
                Seat.status == SeatStatus.locked,
                (Seat.locked_until.is_(None)) | (Seat.locked_until >= now),
            )
        ).all()
        if r[0] is not None
    ]

    locked_rows = locked_rows_seats

    sold_count_global = max(0, int(inv.total or 0) - int(inv.available or 0))
    stats = SeatStats(
        total=int(inv.total or 0),
        available=int(inv.available or 0),
        soldCount=sold_count_global,
        lockedCount=len(locked_rows),
    )
    return SeatStateRead(sessionId=session_id, ticketTypeId=ticket_type_id, sold=sold_rows, locked=locked_rows, stats=stats)


@router.get("/sessions/{session_id}/ticket-types/{ticket_type_id}/state", response_model=SeatStateRead)
def get_seat_state_by_session_path(
    session_id: int,
    ticket_type_id: int,
    lock_ttl_seconds: int = Query(180, ge=0, le=3600),
    db: Session = Depends(get_db),
):
    # 与上面同逻辑，提供更语义化的 RESTful 路径别名
    now = datetime.utcnow()
    lock_deadline = now - timedelta(seconds=lock_ttl_seconds)

    inv = db.execute(
        select(TicketInventory).where(
            TicketInventory.session_id == session_id,
            TicketInventory.ticket_type_id == ticket_type_id,
        )
    ).scalars().first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory not found")

    sold_rows: List[int] = [
        r[0]
        for r in db.execute(
            select(Ticket.seat_id).where(
                Ticket.session_id == session_id,
                Ticket.ticket_type_id == ticket_type_id,
                Ticket.seat_id.isnot(None),
                Ticket.status.in_([TicketStatus.active, TicketStatus.used]),
            )
        ).all()
        if r[0] is not None
    ]

    locked_rows: List[int] = [
        r[0]
        for r in db.execute(
            select(Ticket.seat_id).where(
                Ticket.session_id == session_id,
                Ticket.ticket_type_id == ticket_type_id,
                Ticket.seat_id.isnot(None),
                Ticket.status == TicketStatus.pending,
                Ticket.created_at >= lock_deadline,
            )
        ).all()
        if r[0] is not None
    ]

    sold_count_global = max(0, int(inv.total or 0) - int(inv.available or 0))
    stats = SeatStats(
        total=int(inv.total or 0),
        available=int(inv.available or 0),
        soldCount=sold_count_global,
        lockedCount=len(locked_rows),
    )
    return SeatStateRead(sessionId=session_id, ticketTypeId=ticket_type_id, sold=sold_rows, locked=locked_rows, stats=stats)


@router.get("/map", response_model=seat_schemas.SeatMapRead)
def seat_map(
    event_id: int,
    session_id: int | None = None,
    ticket_type_id: int | None = None,
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    # overlay sold/locked for provided session/ticket_type
    sold_ids: set[int] = set()
    if session_id is not None:
        q = select(Ticket.seat_id).where(
            Ticket.session_id == session_id,
            Ticket.seat_id.isnot(None),
            Ticket.status.in_([TicketStatus.active, TicketStatus.used]),
        )
        if ticket_type_id is not None:
            q = q.where(Ticket.ticket_type_id == ticket_type_id)
        sold_ids = {sid for (sid,) in db.execute(q) if sid is not None}
    locked_ids: set[int] = {
        sid for (sid,) in db.execute(
            select(Seat.id).where(
                Seat.event_id == event_id,
                Seat.status == SeatStatus.locked,
                (Seat.locked_until.is_(None)) | (Seat.locked_until >= now),
            )
        )
    }
    # load all seats for event
    seats = db.execute(
        select(Seat).where(Seat.event_id == event_id)
    ).scalars().all()

    rows: dict[str | None, list[seat_schemas.SeatItem]] = {}
    total = 0
    sold_cnt = 0
    locked_cnt = 0
    for s in seats:
        total += 1
        if s.id in sold_ids:
            status = "sold"
            sold_cnt += 1
        elif s.id in locked_ids:
            status = "locked"
            locked_cnt += 1
        else:
            status = "available"
        key = getattr(s, "row", None)
        rows.setdefault(key, []).append(
            seat_schemas.SeatItem(
                id=s.id,
                section=getattr(s, "section", None),
                row=getattr(s, "row", None),
                number=getattr(s, "number", None),
                status=status,
            )
        )
    groups = [
        seat_schemas.SeatRowGroup(row=k, seats=v) for k, v in sorted(rows.items(), key=lambda x: (str(x[0] or ""),))
    ]
    available = max(0, total - sold_cnt - locked_cnt)
    stats = SeatStats(total=total, available=available, soldCount=sold_cnt, lockedCount=locked_cnt)
    return seat_schemas.SeatMapRead(
        eventId=event_id,
        sessionId=session_id,
        ticketTypeId=ticket_type_id,
        rows=groups,
        stats=stats,
    )


