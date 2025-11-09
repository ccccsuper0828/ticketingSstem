from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app import crud, models
from app.schemas import event as event_schemas
from app.core.security import require_admin

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 如果未来需要表单+文件上传，可添加 Form/Depends 解析，这里先保持 JSON 简单创建


@router.post("/", response_model=event_schemas.EventRead)
async def create_event(
    payload: event_schemas.EventCreate,
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    if payload.created_by is None:
        payload.created_by = admin_user.id
    return crud.event.create_event(db, payload, cover_image_url=None)


@router.get("/{event_id}", response_model=event_schemas.EventRead)
def read_event(event_id: int, db: Session = Depends(get_db)):
    db_event = crud.event.get_event(db, event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    return db_event


@router.get("/", response_model=List[event_schemas.EventRead])
def list_events(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return crud.event.list_events(db, skip=skip, limit=limit)


@router.put("/{event_id}", response_model=event_schemas.EventRead)
def update_event(
    event_id: int,
    payload: event_schemas.EventUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    db_event = crud.event.update_event(db, event_id, payload)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    return db_event


@router.delete("/{event_id}", response_model=event_schemas.EventRead)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    db_event = crud.event.delete_event(db, event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    return db_event


@router.post("/{event_id}/publish", response_model=event_schemas.EventRead)
def publish_event(
    event_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    db_event = crud.event.publish_event(db, event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    return db_event


# ---------- Multipart create with cover image ----------
async def build_event_create_from_form(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    start_time: str = Form(...),
    end_time: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    status: str = Form("draft"),
) -> event_schemas.EventCreate:
    from datetime import datetime

    start_dt = datetime.fromisoformat(start_time)
    end_dt = datetime.fromisoformat(end_time) if end_time else None
    return event_schemas.EventCreate(
        name=name,
        description=description,
        start_time=start_dt,
        end_time=end_dt,
        location=location,
        status=status,
    )


@router.post("/upload", response_model=event_schemas.EventRead)
async def create_event_with_cover(
    data: event_schemas.EventCreate = Depends(build_event_create_from_form),
    cover_image_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin_user: models.User = Depends(require_admin),
):
    try:
        from app.utils import imageupload
        cover_url = imageupload.save_uploaded_image(cover_image_file, folder="events")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

    data.created_by = admin_user.id
    return crud.event.create_event(db, data, cover_image_url=cover_url)