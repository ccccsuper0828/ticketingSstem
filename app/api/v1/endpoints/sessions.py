from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app import crud, models
from app.schemas import session as session_schemas
from app.core.security import require_admin


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/", response_model=List[session_schemas.SessionRead])
def list_sessions(
    event_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    return crud.session.list_sessions(db, event_id=event_id, skip=skip, limit=limit)


@router.get("/{session_id}", response_model=session_schemas.SessionRead)
def read_session(session_id: int, db: Session = Depends(get_db)):
    row = crud.session.get_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


@router.post("/", response_model=session_schemas.SessionRead)
def create_session(
    payload: session_schemas.SessionCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    return crud.session.create_session(db, payload)


@router.put("/{session_id}", response_model=session_schemas.SessionRead)
def update_session(
    session_id: int,
    payload: session_schemas.SessionUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    row = crud.session.update_session(db, session_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


@router.delete("/{session_id}", response_model=session_schemas.SessionRead)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    row = crud.session.delete_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


