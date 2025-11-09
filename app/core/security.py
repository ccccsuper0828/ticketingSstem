"""Security helpers: token verification and role guards."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas import auth as auth_svc
from app import models
from app.models.enums import UserRole


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    payload = auth_svc.verify_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = payload["sub"]
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if str(current_user.role) != UserRole.admin.value and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user

