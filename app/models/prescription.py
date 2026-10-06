from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

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

    medicine_name = Column(
        String(200),
        nullable=False
    )

    dosage = Column(
        String(100),
        nullable=False
    )

    frequency = Column(
        String(100),
        nullable=False
    )

    duration = Column(
        String(100),
        nullable=False
    )

    instructions = Column(
        String(300),
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True
    )

    medical_record = relationship(
        "MedicalRecord",
        back_populates="prescriptions"
    )