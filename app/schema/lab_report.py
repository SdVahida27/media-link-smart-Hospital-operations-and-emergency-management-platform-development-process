from datetime import date
from pydantic import BaseModel


class LabReportBase(BaseModel):
    medical_record_id: int
    lab_test_request_id: int | None = None
    patient_id: int
    doctor_id: int
    test_name: str
    test_result: str
    remarks: str | None = None
    report_date: date


class LabReportCreate(LabReportBase):
    pass


class LabReportUpdate(BaseModel):
    test_name: str | None = None
    test_result: str | None = None
    remarks: str | None = None
    report_date: date | None = None


class LabReportResponse(LabReportBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True