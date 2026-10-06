from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class MedicineDispensing(Base):
    __tablename__ = "medicine_dispensings"

    id = Column(Integer, primary_key=True, index=True)

    prescription_id = Column(
        Integer,
        ForeignKey("prescriptions.id"),
        nullable=False
    )

    patient_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    medicine_id = Column(
        Integer,
        ForeignKey("medicines.id"),
        nullable=False
    )

    quantity = Column(Integer, nullable=False)

    dispensed_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    dispensed_date = Column(Date, nullable=False)

    status = Column(
        String(30),
        default="DISPENSED",
        nullable=False
    )

    remarks = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)

    prescription = relationship("Prescription")
    patient = relationship(
        "User",
        foreign_keys=[patient_id]
    )
    medicine = relationship("Medicine")
    pharmacist = relationship(
        "User",
        foreign_keys=[dispensed_by]
    )