from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Billing(Base):
    __tablename__ = "billings"

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

    doctor_fee = Column(
        Float,
        nullable=False
    )

    lab_fee = Column(
        Float,
        default=0
    )

    medicine_fee = Column(
        Float,
        default=0
    )

    other_charges = Column(
        Float,
        default=0
    )

    total_amount = Column(
        Float,
        nullable=False
    )

    payment_status = Column(
        String(50),
        default="Pending"
    )

    payment_method = Column(
        String(50),
        nullable=True
    )

    billing_date = Column(
        Date,
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    appointment = relationship(
        "Appointment"
    )

    patient = relationship(
        "User",
        foreign_keys=[patient_id]
    )