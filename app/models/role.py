from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(50), unique=True, nullable=False)

    description = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True)

    users = relationship("User", back_populates="role")