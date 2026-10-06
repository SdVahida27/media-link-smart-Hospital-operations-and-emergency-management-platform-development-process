from datetime import date

from pydantic import BaseModel


class MedicineStockTransactionCreate(BaseModel):
    medicine_id: int
    transaction_type: str
    quantity: int
    reason: str | None = None
    transaction_date: date


class MedicineStockTransactionResponse(BaseModel):
    id: int
    medicine_id: int
    transaction_type: str
    quantity: int
    reason: str | None
    transaction_date: date
    performed_by: int
    is_active: bool

    class Config:
        from_attributes = True