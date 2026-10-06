from datetime import date

from pydantic import BaseModel


class AdmissionCreate(BaseModel):
    patient_id: int
    bed_id: int
    admission_date: date
    reason: str | None = None


class AdmissionUpdate(BaseModel):
    reason: str | None = None
    status: str | None = None


class AdmissionResponse(BaseModel):
    id: int
    patient_id: int
    bed_id: int
    admission_date: date
    discharge_date: date | None
    reason: str | None
    status: str
    is_active: bool

    class Config:
        from_attributes = True