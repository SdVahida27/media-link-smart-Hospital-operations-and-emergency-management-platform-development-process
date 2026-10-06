from datetime import date

from pydantic import BaseModel


class MedicineDispensingCreate(BaseModel):
    prescription_id: int
    medicine_id: int
    quantity: int
    dispensed_date: date
    remarks: str | None = None


class MedicineDispensingResponse(BaseModel):
    id: int
    prescription_id: int
    patient_id: int
    medicine_id: int
    quantity: int
    dispensed_by: int
    dispensed_date: date
    status: str
    remarks: str | None
    is_active: bool

    class Config:
        from_attributes = True