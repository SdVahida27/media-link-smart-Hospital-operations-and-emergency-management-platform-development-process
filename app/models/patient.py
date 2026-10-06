from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    blood_group = Column(String(10), nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    gender = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    emergency_contact = Column(String(20), nullable=True)

    is_active = Column(Boolean, default=True)

    user = relationship("User")