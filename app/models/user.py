from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False
    )

    email = Column(
        String(150),
        unique=True,
        index=True,
        nullable=False
    )

    password = Column(
        String(255),
        nullable=False
    )

    slug = Column(
        String(150),
        unique=True,
        index=True
    )

    first_name = Column(
        String(100),
        nullable=True
    )

    last_name = Column(
        String(100),
        nullable=True
    )

    phone = Column(
        String(20),
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True
    )

    role_id = Column(
        Integer,
        ForeignKey("roles.id"),
        nullable=False
    )

    hospital_id = Column(
        Integer,
        ForeignKey("hospitals.id"),
        nullable=True
    )

    role = relationship(
        "Role",
        back_populates="users"
    )

    hospital = relationship(
        "Hospital",
        back_populates="users"
    )

    doctor = relationship(
        "Doctor",
        back_populates="user",
        uselist=False
    )
    nurse = relationship(
    "Nurse",
    back_populates="user",
    uselist=False
)