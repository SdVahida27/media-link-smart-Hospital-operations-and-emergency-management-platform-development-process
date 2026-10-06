from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
)

from sqlalchemy.orm import relationship

from app.core.database import Base


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=False,
    )

    specialization = Column(String(150), nullable=False)

    qualification = Column(String(200), nullable=False)

    experience = Column(Integer, default=0)

    consultation_fee = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)

    user = relationship(
        "User",
        back_populates="doctor"
    )

    department = relationship(
        "Department",
        back_populates="doctors"
    )
    appointments = relationship(
    "Appointment",
    back_populates="doctor"
)