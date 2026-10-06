from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class LabReport(Base):
    __tablename__ = "lab_reports"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    medical_record_id = Column(
        Integer,
        ForeignKey("medical_records.id"),
        nullable=False
    )

    lab_test_request_id = Column(
        Integer,
        ForeignKey("lab_test_requests.id"),
        nullable=True
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

    test_result = Column(
        Text,
        nullable=False
    )

    remarks = Column(
        Text,
        nullable=True
    )

    report_date = Column(
        Date,
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    medical_record = relationship(
        "MedicalRecord",
        back_populates="lab_reports"
    )

    lab_test_request = relationship(
        "LabTestRequest"
    )

    patient = relationship(
        "User",
        foreign_keys=[patient_id]
    )

    doctor = relationship(
        "Doctor"
    )