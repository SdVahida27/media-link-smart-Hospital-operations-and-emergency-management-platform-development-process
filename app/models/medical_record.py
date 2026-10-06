from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=False
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

    symptoms = Column(
        Text,
        nullable=False
    )

    diagnosis = Column(
        Text,
        nullable=False
    )

    treatment = Column(
        Text,
        nullable=False
    )

    notes = Column(
        Text,
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True
    )

    appointment = relationship(
    "Appointment",
    back_populates="medical_records"
)

    patient = relationship(
        "User",
        foreign_keys=[patient_id]
    )

    doctor = relationship(
        "Doctor"
    )
    prescriptions = relationship(
    "Prescription",
    back_populates="medical_record"
)
    lab_reports = relationship(
    "LabReport",
    back_populates="medical_record"
)