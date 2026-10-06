from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class MedicineStockTransaction(Base):
    __tablename__ = "medicine_stock_transactions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    medicine_id = Column(
        Integer,
        ForeignKey("medicines.id"),
        nullable=False
    )

    transaction_type = Column(
        String(20),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    reason = Column(
        Text,
        nullable=True
    )

    transaction_date = Column(
        Date,
        nullable=False
    )

    performed_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    medicine = relationship(
        "Medicine"
    )

    user = relationship(
        "User"
    )