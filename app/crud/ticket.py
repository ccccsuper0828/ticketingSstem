from typing import List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import select, update, text
from sqlalchemy.sql import func

from app.models.ticket import Ticket
from app.models.enums import TicketStatus
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.utils.qrcode_gen import generate_qr_image, generate_qr_png_bytes
from app.models.inventory import TicketInventory
from app.models.user import User
from app.models.ticket_type import TicketType
from app.models.session import EventSession
from app.models.seat import Seat
from app.models.enums import SeatStatus
from app.models.payment import Payment
from app.models.enums import PaymentMethod, PaymentStatus
from app.core.redis_client import get_redis


def generate_qr_code() -> bytes:
    unique = uuid4().hex
    # 模拟验证链接内容，扫描后会看到这个 URL（无需真实可访问）
    content = f"https://mock-verify.local/qr/{unique}"
    return generate_qr_png_bytes(content)


def get_ticket(db: Session, ticket_id: int) -> Optional[Ticket]:
    return db.get(Ticket, ticket_id)


def list_tickets(db: Session, skip: int = 0, limit: int = 10) -> List[Ticket]:
    stmt = select(Ticket).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def create_ticket(db: Session, data: TicketCreate) -> Ticket:
    db_ticket = Ticket(
        ticket_type_id=data.ticket_type_id,
        session_id=data.session_id,
        user_id=data.user_id,
        seat_id=data.seat_id,
        status=TicketStatus.pending,
        qr_code=generate_qr_code(),  # 存为 PNG 二进制
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


def update_ticket(db: Session, ticket_id: int, data: TicketUpdate) -> Optional[Ticket]:
    db_ticket = get_ticket(db, ticket_id)
    if not db_ticket:
        return None
    if data.seat_id is not None:
        db_ticket.seat_id = data.seat_id
    if data.status is not None:
        # trust value; in production map/validate to enum set
        db_ticket.status = data.status  # type: ignore[assignment]
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


def delete_ticket(db: Session, ticket_id: int) -> Optional[Ticket]:
    db_ticket = get_ticket(db, ticket_id)
    if not db_ticket:
        return None
    db.delete(db_ticket)
    db.commit()
    return db_ticket


def purchase_ticket_with_credit(
    db: Session,
    *,
    user_id: int,
    session_id: int,
    ticket_type_id: int,
    seat_id: Optional[int] = None,
) -> Ticket:
    """
    原子扣减库存与用户余额，创建已支付票券。无消息队列，依赖数据库原子性。
    """
    # 查询库存以取价；稍后用条件更新保证并发安全
    inv = db.execute(
        select(TicketInventory).where(
            TicketInventory.session_id == session_id,
            TicketInventory.ticket_type_id == ticket_type_id,
        )
    ).scalars().first()
    if not inv:
        # 尝试从 TicketType/EventSession 引导创建库存（避免前端首次下单 404）
        tt = db.execute(select(TicketType).where(TicketType.id == ticket_type_id)).scalars().first()
        es = db.execute(select(EventSession).where(EventSession.id == session_id)).scalars().first()
        if not tt:
            raise ValueError("Inventory not found")
        # 计算默认总量与可用量
        tt_total = int(tt.totalstock or 0)
        tt_avail = int(getattr(tt, "availablestock", 0) or 0)
        es_cap = int(es.capacity if es else 0)
        inferred_total = max(tt_avail, tt_total)
        if es_cap > 0:
            inferred_total = min(inferred_total or es_cap, es_cap)
        inferred_total = max(inferred_total, 0)
        new_inv = TicketInventory(
            session_id=session_id,
            ticket_type_id=ticket_type_id,
            price=int(tt.price or 0),
            total=inferred_total,
            available=inferred_total,
        )
        db.add(new_inv)
        db.commit()
        db.refresh(new_inv)
        inv = new_inv
    price = int(inv.price or 0)

    # If seat specified, validate it belongs to the same event as session and is available (or lockable)
    target_event_id: Optional[int] = None
    if seat_id is not None:
        es = db.execute(select(EventSession).where(EventSession.id == session_id)).scalars().first()
        if not es:
            raise ValueError("Session not found")
        target_event_id = int(getattr(es, "event_id", None) or 0)

    # Redis 基于会话+票种的互斥锁（可选）
    lock = None
    seat_lock = None
    rds = get_redis()
    try:
        if rds:
            lock = rds.lock(f"purchase:{session_id}:{ticket_type_id}", timeout=5, blocking_timeout=5)
            lock.acquire()
            if seat_id is not None:
                seat_lock = rds.lock(f"seat:{seat_id}", timeout=5, blocking_timeout=5)
                seat_lock.acquire()
        # 0) If seat specified, perform optimistic lock on seat row
        if seat_id is not None:
            # lock only if seat belongs to event and is not currently locked/sold
            seat_lock_res = db.execute(
                update(Seat)
                .where(
                    Seat.id == seat_id,
                    Seat.event_id == target_event_id,
                    Seat.status == SeatStatus.available,
                )
                .values(
                    status=SeatStatus.locked,
                    locked_until=func.date_add(func.now(), text("INTERVAL 180 SECOND")),  # MySQL compatible
                )
            )
            if seat_lock_res.rowcount != 1:
                raise RuntimeError("Seat not available")

        # 1) 扣减库存（仅当 available > 0）
        inv_res = db.execute(
            update(TicketInventory)
            .where(
                TicketInventory.session_id == session_id,
                TicketInventory.ticket_type_id == ticket_type_id,
                TicketInventory.available > 0,
            )
            .values(available=TicketInventory.available - 1)
        )
        if inv_res.rowcount != 1:
            raise RuntimeError("Out of stock")

        # 2) 扣减用户积分（仅当 credit >= price）
        credit_res = db.execute(
            update(User)
            .where(User.id == user_id, User.credit >= price)
            .values(credit=User.credit - price)
        )
        if credit_res.rowcount != 1:
            # 触发回滚
            raise RuntimeError("Insufficient credit")

        # 3) 创建票券（已支付）
        db_ticket = Ticket(
            ticket_type_id=ticket_type_id,
            session_id=session_id,
            user_id=user_id,
            seat_id=seat_id,
            status=TicketStatus.active,
            qr_code=generate_qr_code(),
            purchase_time=func.now(),
        )
        db.add(db_ticket)
        # 刷新以取回 ID
        db.flush()
        db.refresh(db_ticket)

        # 3.5) 记录支付
        payment = Payment(
            ticket_id=db_ticket.id,
            user_id=user_id,
            amount=price,
            paymentmethod=PaymentMethod.credit,
            status=PaymentStatus.paid,
            transaction_id=uuid4().hex,
            payment_time=func.now(),
        )
        db.add(payment)

        # 4) If seat locked earlier, mark as sold
        if seat_id is not None:
            db.execute(
                update(Seat)
                .where(Seat.id == seat_id)
                .values(status=SeatStatus.sold, locked_until=None)
            )

        db.commit()
        return db_ticket
    except Exception:
        db.rollback()
        raise
    finally:
        try:
            if seat_lock:
                seat_lock.release()
        except Exception:
            pass
        try:
            if lock:
                lock.release()
        except Exception:
            pass


