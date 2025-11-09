from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app import crud
from app.schemas import user as user_schemas
from app.core.security import get_current_user
from app import models


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=user_schemas.UserRead)
def create_user(user: user_schemas.UserCreate, db: Session = Depends(get_db)):
    exists = crud.user.get_user_by_email(db, email=user.email)
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.user.create_user(db=db, user=user)


@router.get("/{user_id}", response_model=user_schemas.UserRead)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.user.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.get("/", response_model=List[user_schemas.UserRead])
def list_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.user.get_users(db, skip=skip, limit=limit)


@router.put("/{user_id}", response_model=user_schemas.UserRead)
def update_user(user_id: int, user: user_schemas.UserUpdate, db: Session = Depends(get_db)):
    db_user = crud.user.update_user(db, user_id=user_id, user=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete("/{user_id}", response_model=user_schemas.UserRead)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.user.delete_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.get("/me", response_model=user_schemas.UserRead)
def read_me(current_user: models.User = Depends(get_current_user)) -> models.User:
    return current_user


@router.put("/me", response_model=user_schemas.UserRead)
def update_me(
    payload: user_schemas.UserMeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # 限制仅可改本人的非敏感字段
    update = user_schemas.UserUpdate(
        username=payload.username,
        email=payload.email,
        phone=payload.phone,
    )
    db_user = crud.user.update_user(db, user_id=current_user.id, user=update)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


