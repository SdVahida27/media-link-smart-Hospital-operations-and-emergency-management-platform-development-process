from datetime import date
from pydantic import BaseModel


class LabTestRequestBase(BaseModel):
    medical_record_id: int
    patient_id: int
    doctor_id: int
    test_name: str
    clinical_reason: str | None = None
    priority: str = "NORMAL"
    status: str = "REQUESTED"
    requested_date: date


class LabTestRequestCreate(LabTestRequestBase):
    pass


class LabTestRequestUpdate(BaseModel):
    test_name: str | None = None
    clinical_reason: str | None = None
    priority: str | None = None
    status: str | None = None


class LabTestRequestResponse(LabTestRequestBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
class LabTestRequestStatusUpdate(BaseModel):
    status: str