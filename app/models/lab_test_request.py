from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class LabTestRequest(Base):
    __tablename__ = "lab_test_requests"

    id = Column(Integer, primary_key=True, index=True)

    medical_record_id = Column(
        Integer,
        ForeignKey("medical_records.id"),
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

    test_name = Column(
        String(200),
        nullable=False
    )

    clinical_reason = Column(
        Text,
        nullable=True
    )

    priority = Column(
        String(30),
        default="NORMAL",
        nullable=False
    )

    status = Column(
        String(30),
        default="REQUESTED",
        nullable=False
    )

    requested_date = Column(
        Date,
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    medical_record = relationship(
        "MedicalRecord"
    )

    patient = relationship(
        "User",
        foreign_keys=[patient_id]
    )

    doctor = relationship(
        "Doctor",
        foreign_keys=[doctor_id]
    )