from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, String, func

from app.db.base import Base
from app.models.enums import UserRole


DEFAULT_AVATAR = "https://avatarfiles.alphacoders.com/368/thumb-1920-368375.png"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(150), nullable=False)
    email = Column(String(254), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole, name="user_role"), nullable=False, default=UserRole.customer)
    avatar = Column(String(512), nullable=True, default=DEFAULT_AVATAR)
    credit = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


