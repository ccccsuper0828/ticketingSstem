from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr
from pydantic import ConfigDict


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    avatar: Optional[str] = None
    phone: Optional[str] = None

class UserMeUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    isAdmin: bool
    roles: List[str]
    userId: int


class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    avatar: Optional[str] = None
    phone: Optional[str] = None
    credit: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


