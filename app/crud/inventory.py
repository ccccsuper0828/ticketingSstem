from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.inventory import TicketInventory
from app.schemas.inventory import InventoryCreate, InventoryUpdate


def get_inventory(db: Session, inventory_id: int) -> Optional[TicketInventory]:
    return db.get(TicketInventory, inventory_id)


def get_inventory_by_key(db: Session, session_id: int, ticket_type_id: int) -> Optional[TicketInventory]:
    stmt = select(TicketInventory).where(
        TicketInventory.session_id == session_id,
        TicketInventory.ticket_type_id == ticket_type_id,
    )
    return db.execute(stmt).scalars().first()


def list_inventory(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    session_id: Optional[int] = None,
    ticket_type_id: Optional[int] = None,
) -> List[TicketInventory]:
    stmt = select(TicketInventory)
    if session_id is not None:
        stmt = stmt.where(TicketInventory.session_id == session_id)
    if ticket_type_id is not None:
        stmt = stmt.where(TicketInventory.ticket_type_id == ticket_type_id)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())


def create_inventory(db: Session, data: InventoryCreate) -> TicketInventory:
    existing = get_inventory_by_key(db, data.session_id, data.ticket_type_id)
    if existing:
        return existing
    row = TicketInventory(
        session_id=data.session_id,
        ticket_type_id=data.ticket_type_id,
        price=data.price,
        total=data.total,
        available=data.total,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_inventory(db: Session, inventory_id: int, data: InventoryUpdate) -> Optional[TicketInventory]:
    row = get_inventory(db, inventory_id)
    if not row:
        return None
    if data.price is not None:
        row.price = data.price
    if data.total is not None:
        # Adjust available proportionally only if expanding from zero; otherwise keep manual control
        delta = data.total - row.total
        row.total = data.total
        row.available = max(0, row.available + delta)
    if data.available is not None:
        row.available = max(0, data.available)
    db.commit()
    db.refresh(row)
    return row


