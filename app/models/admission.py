from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Admission(Base):
    __tablename__ = "admissions"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    bed_id = Column(
        Integer,
        ForeignKey("beds.id"),
        nullable=False
    )

    admission_date = Column(
        Date,
        nullable=False
    )

    discharge_date = Column(
        Date,
        nullable=True
    )

    reason = Column(
        String(500),
        nullable=True
    )

    status = Column(
        String(30),
        default="ADMITTED",
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    patient = relationship("User")
    bed = relationship("Bed")