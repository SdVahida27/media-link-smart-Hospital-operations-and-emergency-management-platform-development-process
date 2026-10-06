from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Bed(Base):
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True)

    room_id = Column(
        Integer,
        ForeignKey("rooms.id"),
        nullable=False
    )

    bed_number = Column(
        String(50),
        nullable=False
    )

    bed_type = Column(
        String(50),
        nullable=False
    )

    status = Column(
        String(30),
        default="AVAILABLE",
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    room = relationship("Room")