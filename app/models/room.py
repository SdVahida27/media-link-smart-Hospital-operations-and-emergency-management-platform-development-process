from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)

    hospital_id = Column(
        Integer,
        ForeignKey("hospitals.id"),
        nullable=False
    )

    room_number = Column(
        String(50),
        nullable=False
    )

    room_type = Column(
        String(50),
        nullable=False
    )

    floor_number = Column(
        Integer,
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True
    )

    hospital = relationship("Hospital")