from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import require_admin
from app import models
from app.models.enums import EventStatus, SeatStatus
from app.models.event import Event
from app.models.session import EventSession
from app.models.ticket_type import TicketType
from app.models.inventory import TicketInventory
from app.models.seat import Seat


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/seed", tags=["dev"])
def seed_mock_data(db: Session = Depends(get_db), _: models.User = Depends(require_admin)) -> dict:
    """
    创建一套可用的 Mock 数据：Event -> Session -> TicketTypes -> Inventory -> Seats
    可重复调用（幂等）。
    """
    # 1) Event
    event = db.query(Event).filter(Event.name == "Mock Concert").first()
    if not event:
        event = Event(
            name="Mock Concert",
            description="Demo event",
            start_time=datetime.utcnow() + timedelta(days=1),
            end_time=None,
            location="Demo Hall",
            status=EventStatus.published,
            created_by=None,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

    # 2) Session
    session = db.query(EventSession).filter(EventSession.event_id == event.id).first()
    if not session:
        session = EventSession(
            event_id=event.id,
            sessiontime=datetime.utcnow() + timedelta(days=1, hours=2),
            capacity=100,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # 3) TicketTypes
    tt_std = db.query(TicketType).filter(TicketType.eventid == event.id, TicketType.name == "Standard").first()
    if not tt_std:
        tt_std = TicketType(eventid=event.id, name="Standard", price=100, totalstock=100, availablestock=100)
        db.add(tt_std)
        db.commit()
        db.refresh(tt_std)
    tt_vip = db.query(TicketType).filter(TicketType.eventid == event.id, TicketType.name == "VIP").first()
    if not tt_vip:
        tt_vip = TicketType(eventid=event.id, name="VIP", price=200, totalstock=20, availablestock=20)
        db.add(tt_vip)
        db.commit()
        db.refresh(tt_vip)

    # 4) Inventory for session+type
    for tt in [tt_std, tt_vip]:
        inv = (
            db.query(TicketInventory)
            .filter(
                TicketInventory.session_id == session.id,
                TicketInventory.ticket_type_id == tt.id,
            )
            .first()
        )
        if not inv:
            total = min(int(tt.availablestock or tt.totalstock or 0), int(session.capacity or 0) or 10)
            inv = TicketInventory(
                session_id=session.id,
                ticket_type_id=tt.id,
                price=int(tt.price or 0),
                total=total,
                available=total,
            )
            db.add(inv)
            db.commit()

    # 5) Seats for event
    seat_count = db.query(Seat).filter(Seat.eventid == event.id).count()
    if seat_count < 50:
        to_create = 50 - seat_count
        for idx in range(seat_count + 1, seat_count + 1 + to_create):
            db.add(Seat(eventid=event.id, section="A", row="R1", number=str(idx), status=SeatStatus.available))
        db.commit()

    return {
        "eventId": event.id,
        "sessionId": session.id,
        "ticketTypeIds": [tt_std.id, tt_vip.id],
        "seededSeats": max(50, seat_count),
        "message": "Mock data ready",
    }


@router.post("/seed_seats", tags=["dev"])
def seed_seats(
    event_id: int | None = None,
    rows: str = "A",
    count: int = 200,
    start: int = 1,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
) -> dict:
    """
    批量生成座位：
    - event_id: 所属活动
    - rows: 逗号分隔的行标（如 "A,B,C"）
    - count: 每行生成的数量（从 start 开始，连续 count 个）
    - start: 起始编号（默认 1）
    已存在的 (event_id, row, number) 不会重复创建。
    """
    row_labels = [r.strip() for r in rows.split(",") if r.strip()]
    created = 0
    # 需要处理的 event 列表
    event_ids: List[int]
    if event_id is None:
        event_ids = [e.id for e in db.query(Event.id).all()]
    else:
        event_ids = [event_id]
    for eid in event_ids:
        for row_label in row_labels:
            batch: List[Seat] = []
            for i in range(start, start + max(0, count)):
                num = str(i)
                exists = (
                    db.query(Seat.id)
                    .filter(
                        Seat.event_id == eid,
                        Seat.row == row_label,
                        Seat.number == num,
                    )
                    .first()
                )
                if exists:
                    continue
                batch.append(
                    Seat(
                        event_id=eid,
                        section=row_label,  # 可选：用 section=行标
                        row=row_label,
                        number=num,
                        status=SeatStatus.available,
                    )
                )
            if batch:
                db.add_all(batch)
                db.commit()
                created += len(batch)
    return {"eventIds": event_ids, "rows": row_labels, "created": created}


@router.post("/seed_seats_sessions", tags=["dev"])
def seed_seats_for_sessions(
    count: int = 50,
    start: int = 1,
    event_id: int | None = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
) -> dict:
    """
    为每个 session 生成 count 个座位，行标为 S{session_id}，编号从 start 开始。
    如果提供 event_id，仅处理该活动下的 sessions；否则处理全部 sessions。
    """
    q = db.query(EventSession)
    if event_id is not None:
        q = q.filter(EventSession.event_id == event_id)
    sessions = q.all()
    total_created = 0
    for s in sessions:
        row_label = f"S{s.id}"
        batch = []
        for i in range(start, start + max(0, count)):
            num = str(i)
            exists = (
                db.query(Seat.id)
                .filter(
                    Seat.event_id == s.event_id,
                    Seat.row == row_label,
                    Seat.number == num,
                )
                .first()
            )
            if exists:
                continue
            batch.append(
                Seat(
                    event_id=s.event_id,
                    section=row_label,
                    row=row_label,
                    number=num,
                    status=SeatStatus.available,
                )
            )
        if batch:
            db.add_all(batch)
            db.commit()
            total_created += len(batch)
    return {"handledSessions": len(sessions), "created": total_created}


@router.post("/seed_sessions", tags=["dev"])
def seed_sessions(
    num: int = 3,
    capacity: int = 200,
    spacing_minutes: int = 120,
    start_in_minutes: int = 60,
    event_id: int | None = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
) -> dict:
    """
    为每个活动创建至少 num 个 session，并为每个 session 对每个票种补齐 inventory。
    - spacing_minutes: 相邻 session 的时间间隔
    - start_in_minutes: 第一个 session 距现在的时间
    - capacity: session 容量，用于默认库存上限
    """
    now = datetime.utcnow()
    ev_q = db.query(Event)
    if event_id is not None:
        ev_q = ev_q.filter(Event.id == event_id)
    events = ev_q.all()
    created_sessions = 0
    created_inventories = 0
    for ev in events:
        existing = db.query(EventSession).filter(EventSession.event_id == ev.id).order_by(EventSession.id).all()
        need = max(0, num - len(existing))
        # 生成需要的 session
        for i in range(need):
            base = ev.start_time or now
            # 为不同活动添加轻微错位，避免所有活动同一时间
            offset = (ev.id % 12) * 5
            st = base + timedelta(minutes=start_in_minutes + i * spacing_minutes + offset)
            s = EventSession(event_id=ev.id, sessiontime=st, capacity=capacity)
            db.add(s)
            db.commit()
            db.refresh(s)
            created_sessions += 1
            # 为该 session 的每个票种建立库存
            types = db.query(TicketType).filter((TicketType.event_id == ev.id) | (TicketType.eventid == ev.id)).all()
            for tt in types:
                inv = (
                    db.query(TicketInventory)
                    .filter(
                        TicketInventory.session_id == s.id,
                        TicketInventory.ticket_type_id == tt.id,
                    )
                    .first()
                )
                if inv:
                    continue
                total = min(capacity, int(getattr(tt, "availablestock", 0) or getattr(tt, "totalstock", 0) or capacity))
                inv = TicketInventory(
                    session_id=s.id,
                    ticket_type_id=tt.id,
                    price=int(getattr(tt, "price", 0) or 0),
                    total=total,
                    available=total,
                )
                db.add(inv)
                db.commit()
                created_inventories += 1
    return {"handledEvents": len(events), "createdSessions": created_sessions, "createdInventories": created_inventories}

