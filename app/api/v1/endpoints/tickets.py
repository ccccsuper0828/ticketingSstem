from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app import crud
from app.schemas import ticket as ticket_schemas
from app.schemas import inventory as inventory_schemas
from app.core.security import require_admin, get_current_user
from app import models
from app.schemas.ticket import TicketListItem
from app.models.payment import Payment
from app.models.refund import Refund
from app.models.enums import RefundStatus, TicketStatus
from sqlalchemy import select, update
from app.schemas import refund as refund_schemas


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------- Inventory endpoints (GET is public read; mutations are admin) ---------
@router.get("/inventory", response_model=List[inventory_schemas.InventoryRead])
def list_inventory(
    skip: int = 0,
    limit: int = 50,
    session_id: int | None = None,
    ticket_type_id: int | None = None,
    event_id: int | None = None,  # accepted for compatibility; currently unused
    db: Session = Depends(get_db),
):
    return crud.inventory.list_inventory(db, skip=skip, limit=limit, session_id=session_id, ticket_type_id=ticket_type_id)


@router.post("/inventory", response_model=inventory_schemas.InventoryRead)
def create_inventory(
    payload: inventory_schemas.InventoryCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    return crud.inventory.create_inventory(db, payload)


@router.put("/inventory/{inventory_id}", response_model=inventory_schemas.InventoryRead)
def update_inventory(
    inventory_id: int,
    payload: inventory_schemas.InventoryUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    row = crud.inventory.update_inventory(db, inventory_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return row


# --------- Purchase & Seckill (place BEFORE /{ticket_id} for clarity) ---------
@router.post("/purchase", response_model=ticket_schemas.TicketRead)
def purchase_ticket(
    payload: ticket_schemas.TicketPurchase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    try:
        return crud.ticket.purchase_ticket_with_credit(
            db,
            user_id=current_user.id,
            session_id=payload.session_id,
            ticket_type_id=payload.ticket_type_id,
            seat_id=payload.seat_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        msg = str(e)
        if "stock" in msg:
            raise HTTPException(status_code=409, detail="Out of stock")
        if "credit" in msg:
            raise HTTPException(status_code=402, detail="Insufficient credit")
        raise HTTPException(status_code=400, detail=msg)


@router.post("/purchase/", response_model=ticket_schemas.TicketRead)
def purchase_ticket_trailing_slash(
    payload: ticket_schemas.TicketPurchase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return purchase_ticket(payload, db=db, current_user=current_user)


@router.post("/seckill", response_model=ticket_schemas.TicketRead)
def seckill_ticket(
    payload: ticket_schemas.TicketPurchase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return purchase_ticket(payload, db=db, current_user=current_user)


@router.post("/", response_model=ticket_schemas.TicketRead)
def create_ticket(
    payload: ticket_schemas.TicketCreate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    return crud.ticket.create_ticket(db, payload)


@router.get("/{ticket_id}", response_model=ticket_schemas.TicketRead)
def read_ticket(ticket_id: int, db: Session = Depends(get_db)):
    db_ticket = crud.ticket.get_ticket(db, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return db_ticket


@router.get("/", response_model=List[ticket_schemas.TicketRead])
def list_tickets(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.ticket.list_tickets(db, skip=skip, limit=limit)


@router.get("/my", response_model=List[TicketListItem])
def list_my_tickets(
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = select(models.Ticket).where(models.Ticket.user_id == current_user.id)
    if status:
        q = q.where(models.Ticket.status == status)
    q = q.offset(skip).limit(limit)
    tickets = list(db.execute(q).scalars().all())
    # attach price from payments (latest)
    items: List[TicketListItem] = []
    for t in tickets:
        p = db.execute(select(Payment).where(Payment.ticket_id == t.id).order_by(Payment.id.desc()).limit(1)).scalars().first()
        price = int(getattr(p, "amount", 0) or 0)
        items.append(
            TicketListItem(
                id=t.id,
                user_id=t.user_id,
                session_id=t.session_id,
                ticket_type_id=t.ticket_type_id,
                seat_id=t.seat_id,
                status=str(t.status),
                price=price,
                created_at=t.created_at,
            )
        )
    return items


@router.post("/{ticket_id}/refund-request", response_model=refund_schemas.RefundRead)
def create_refund_request(
    ticket_id: int,
    payload: refund_schemas.RefundRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # 校验票属于本人且状态可退款且不存在待处理申请
    t = crud.ticket.get_ticket(db, ticket_id)
    if not t or t.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if str(t.status) not in [TicketStatus.active, TicketStatus.used]:
        raise HTTPException(status_code=409, detail="Ticket not refundable")
    existing = db.execute(
        select(Refund).where(Refund.ticket_id == ticket_id, Refund.status.in_([RefundStatus.requested, RefundStatus.approved, RefundStatus.rejected]) == False)  # noqa: E712
    ).scalars().first()
    # 更稳妥：查最近一条状态为 requested/pending
    existing = db.execute(
        select(Refund).where(Refund.ticket_id == ticket_id, Refund.status == RefundStatus.requested)
    ).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Refund already requested")
    # 金额取支付记录或库存价
    p = db.execute(select(Payment).where(Payment.ticket_id == ticket_id).order_by(Payment.id.desc()).limit(1)).scalars().first()
    amount = int(getattr(p, "amount", 0) or 0)
    ref = Refund(ticket_id=t.id, user_id=current_user.id, amount=amount, reason=payload.reason or None, status=RefundStatus.requested)
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


@router.get("/refund-requests", response_model=List[refund_schemas.RefundRead])
def list_refund_requests(
    status: str | None = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    q = select(Refund)
    if status:
        q = q.where(Refund.status == status)
    q = q.offset(skip).limit(limit)
    return list(db.execute(q).scalars().all())


@router.post("/refund-requests/{refund_id}/approve", response_model=refund_schemas.RefundRead)
def approve_refund_request(
    refund_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    ref = db.get(Refund, refund_id)
    if not ref:
        raise HTTPException(status_code=404, detail="Refund not found")
    if str(ref.status) != RefundStatus.requested:
        raise HTTPException(status_code=409, detail="Refund not in request state")
    # 加载 ticket
    t = crud.ticket.get_ticket(db, ref.ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    # 原子审批
    try:
        # 票置 refunded
        t.status = TicketStatus.refunded
        # 恢复库存
        inv_res = db.execute(
            update(models.TicketInventory)
            .where(
                models.TicketInventory.session_id == t.session_id,
                models.TicketInventory.ticket_type_id == t.ticket_type_id,
            )
            .values(available=models.TicketInventory.available + 1)
        )
        # 释放座位
        if t.seat_id is not None:
            db.execute(
                update(models.Seat)
                .where(models.Seat.id == t.seat_id)
                .values(status=models.enums.SeatStatus.available, locked_until=None)
            )
        # 返还 credit
        db.execute(
            update(models.User).where(models.User.id == t.user_id).values(credit=models.User.credit + int(ref.amount or 0))
        )
        # 更新退款状态
        ref.status = RefundStatus.approved
        ref.reviewed_by = admin.id
        db.commit()
        db.refresh(ref)
        return ref
    except Exception:
        db.rollback()
        raise


@router.post("/refund-requests/{refund_id}/reject", response_model=refund_schemas.RefundRead)
def reject_refund_request(
    refund_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    ref = db.get(Refund, refund_id)
    if not ref:
        raise HTTPException(status_code=404, detail="Refund not found")
    if str(ref.status) != RefundStatus.requested:
        raise HTTPException(status_code=409, detail="Refund not in request state")
    ref.status = RefundStatus.rejected
    ref.reviewed_by = admin.id
    db.commit()
    db.refresh(ref)
    return ref


@router.put("/{ticket_id}", response_model=ticket_schemas.TicketRead)
def update_ticket(
    ticket_id: int,
    payload: ticket_schemas.TicketUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    db_ticket = crud.ticket.update_ticket(db, ticket_id, payload)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return db_ticket


@router.delete("/{ticket_id}", response_model=ticket_schemas.TicketRead)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_admin),
):
    db_ticket = crud.ticket.delete_ticket(db, ticket_id)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return db_ticket

