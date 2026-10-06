from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    Date,
    Time,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    patient_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False
    )

    appointment_date = Column(
        Date,
        nullable=False
    )

    appointment_time = Column(
        Time,
        nullable=False
    )

    reason = Column(
        String(500),
        nullable=False
    )

    status = Column(
        String(50),
        default="Pending"
    )

    is_active = Column(
        Boolean,
        default=True
    )

    patient = relationship(
        "User",
        foreign_keys=[patient_id]
    )

    doctor = relationship(
        "Doctor",
        back_populates="appointments"
    )
    medical_records = relationship(
    "MedicalRecord",
    back_populates="appointment"
)