from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app import models
from app.models.enums import TicketStatus, UserRole
from app.models.ticket import Ticket
from app.models.user import User
from app.models.inventory import TicketInventory


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _parse_range(range_str: str) -> timedelta:
    if not range_str:
        return timedelta(days=7)
    try:
        if range_str.endswith("d"):
            days = int(range_str[:-1])
            return timedelta(days=days)
        # default fallback
        val = int(range_str)
        return timedelta(days=val)
    except Exception:
        return timedelta(days=7)


@router.get("/overview")
def analytics_overview(range: str = Query("7d"), db: Session = Depends(get_db)) -> Dict[str, float]:
    period = _parse_range(range)
    now = datetime.utcnow()
    start = now - period

    # Staff on duty: use count of admin accounts as a proxy for staff
    staff_on_duty = db.query(User).filter(User.role == UserRole.admin).count()

    # New users in range
    new_users = db.query(User).filter(User.created_at >= start, User.created_at <= now).count()

    # New orders (paid tickets) in range
    new_orders = (
        db.query(Ticket)
        .filter(
            Ticket.status == TicketStatus.active,
            Ticket.purchase_time.isnot(None),
            Ticket.purchase_time >= start,
            Ticket.purchase_time <= now,
        )
        .count()
    )

    # Sell-through rate: total sold / total inventory
    inventory_rows = db.execute(select(TicketInventory.total, TicketInventory.available)).all()
    total_capacity = 0
    total_sold = 0
    for total, available in inventory_rows:
        total_capacity += int(total or 0)
        total_sold += max(0, int(total or 0) - int(available or 0))
    sell_through_rate = 0.0
    if total_capacity > 0:
        sell_through_rate = round(100.0 * total_sold / total_capacity, 2)

    return {
        "staffOnDuty": staff_on_duty,
        "newUsers": new_users,
        "newOrders": new_orders,
        "sellThroughRate": sell_through_rate,
    }


@router.get("/sales-by-day")
def sales_by_day(range: str = Query("7d"), db: Session = Depends(get_db)) -> Dict[str, List]:
    period = _parse_range(range)
    now = datetime.utcnow()
    start = now - period

    # Aggregate paid tickets by day
    day_counts: List[Tuple[date, int]] = (
        db.execute(
            select(func.date(Ticket.purchase_time).label("day"), func.count(Ticket.id))
            .where(
                Ticket.status == TicketStatus.active,
                Ticket.purchase_time.isnot(None),
                Ticket.purchase_time >= start,
                Ticket.purchase_time <= now,
            )
            .group_by(func.date(Ticket.purchase_time))
            .order_by(func.date(Ticket.purchase_time))
        )
        .all()
    )
    by_day: Dict[str, int] = {str(row[0]): int(row[1]) for row in day_counts if row[0] is not None}

    # Build continuous labels
    labels: List[str] = []
    values: List[int] = []
    cursor = start.date()
    end_day = now.date()
    while cursor <= end_day:
        key = str(cursor)
        labels.append(key)
        values.append(by_day.get(key, 0))
        cursor += timedelta(days=1)
    return {"labels": labels, "values": values}


@router.get("/order-status-distribution")
def order_status_distribution(range: str = Query("7d"), db: Session = Depends(get_db)) -> Dict[str, int]:
    period = _parse_range(range)
    now = datetime.utcnow()
    start = now - period

    base_filters = [Ticket.purchase_time.isnot(None), Ticket.purchase_time >= start, Ticket.purchase_time <= now]
    paid = (
        db.query(Ticket)
        .filter(Ticket.status == TicketStatus.active, *base_filters)
        .count()
    )
    pending = (
        db.query(Ticket)
        .filter(Ticket.status == TicketStatus.pending, Ticket.created_at >= start, Ticket.created_at <= now)
        .count()
    )
    refunded = (
        db.query(Ticket)
        .filter(Ticket.status == TicketStatus.refunded, *base_filters)
        .count()
    )
    cancelled = (
        db.query(Ticket)
        .filter(Ticket.status == TicketStatus.cancelled, *base_filters)
        .count()
    )
    failed = 0  # 没有失败状态，返回 0 以兼容前端饼图

    return {"Paid": paid, "Pending": pending, "Refunded": refunded, "Cancelled": cancelled, "Failed": failed}


