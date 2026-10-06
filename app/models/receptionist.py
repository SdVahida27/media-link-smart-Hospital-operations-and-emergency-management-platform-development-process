from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Receptionist(Base):
    __tablename__ = "receptionists"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    qualification = Column(String(200), nullable=True)

    experience_years = Column(Integer, nullable=True)

    is_active = Column(Boolean, default=True)

    user = relationship("User")