from sqlalchemy import Boolean, Column, Integer, String, Text
from app.core.database import Base


class Medicine(Base):
    __tablename__ = "medicines"

    id = Column(Integer, primary_key=True, index=True)

    hospital_id = Column(
        Integer,
        nullable=False
    )

    medicine_name = Column(
        String(200),
        nullable=False
    )

    generic_name = Column(
        String(200),
        nullable=True
    )

    category = Column(
        String(100),
        nullable=True
    )

    manufacturer = Column(
        String(200),
        nullable=True
    )

    unit = Column(
        String(50),
        nullable=False
    )

    quantity = Column(
        Integer,
        default=0,
        nullable=False
    )

    reorder_level = Column(
        Integer,
        default=10,
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )