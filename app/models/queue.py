from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Queue(Base):
    __tablename__ = "queues"

    id = Column(Integer, primary_key=True, index=True)

    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=False,
        unique=True
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

    token_number = Column(Integer, nullable=False)

    queue_date = Column(Date, nullable=False)

    status = Column(
        String(30),
        default="WAITING",
        nullable=False
    )

    is_active = Column(Boolean, default=True)

    appointment = relationship("Appointment")
    patient = relationship("User")
    doctor = relationship("Doctor")