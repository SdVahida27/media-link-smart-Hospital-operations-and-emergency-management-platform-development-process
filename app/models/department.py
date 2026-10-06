from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    description = Column(String(300), nullable=True)

    is_active = Column(Boolean, default=True)

    hospital_id = Column(
        Integer,
        ForeignKey("hospitals.id"),
        nullable=False
    )

    hospital = relationship(
        "Hospital",
        back_populates="departments"
    )
    doctors = relationship(
    "Doctor",
    back_populates="department"
)
    nurses = relationship(
    "Nurse",
    back_populates="department"
)