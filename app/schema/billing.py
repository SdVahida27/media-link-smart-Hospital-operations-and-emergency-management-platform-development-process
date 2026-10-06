from datetime import date

from pydantic import BaseModel


class BillingBase(BaseModel):
    appointment_id: int
    patient_id: int
    doctor_fee: float
    lab_fee: float = 0
    medicine_fee: float = 0
    other_charges: float = 0
    payment_status: str = "Pending"
    payment_method: str | None = None
    billing_date: date


class BillingCreate(BillingBase):
    pass


class BillingUpdate(BaseModel):
    doctor_fee: float | None = None
    lab_fee: float | None = None
    medicine_fee: float | None = None
    other_charges: float | None = None
    payment_status: str | None = None
    payment_method: str | None = None
    billing_date: date | None = None
    is_active: bool | None = None


class BillingResponse(BillingBase):
    id: int
    total_amount: float
    is_active: bool

    class Config:
        from_attributes = True