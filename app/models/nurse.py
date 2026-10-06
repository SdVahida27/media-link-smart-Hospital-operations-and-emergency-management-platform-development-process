from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Nurse(Base):
    __tablename__ = "nurses"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=False
    )

    qualification = Column(
        String(100),
        nullable=False
    )

    experience = Column(
        Integer,
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    # ========================================================
    # USER RELATIONSHIP
    # ========================================================

    user = relationship(
        "User",
        back_populates="nurse"
    )

    # ========================================================
    # DEPARTMENT RELATIONSHIP
    # ========================================================

    department = relationship(
        "Department",
        back_populates="nurses"
    )