from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(150), nullable=False)

    email = Column(String(150), unique=True, nullable=False)

    phone = Column(String(20), unique=True, nullable=False)

    address = Column(String(300), nullable=False)

    city = Column(String(100), nullable=False)

    state = Column(String(100), nullable=False)

    country = Column(String(100), nullable=False)

    pincode = Column(String(10), nullable=False)

    logo = Column(String(255), nullable=True)

    is_active = Column(Boolean, default=True)

    # One Hospital -> Many Users
    users = relationship("User", back_populates="hospital")
    departments = relationship(
    "Department",
    back_populates="hospital"
)