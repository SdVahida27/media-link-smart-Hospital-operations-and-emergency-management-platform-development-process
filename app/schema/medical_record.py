from pydantic import BaseModel


class MedicalRecordBase(BaseModel):
    appointment_id: int
    patient_id: int
    doctor_id: int
    symptoms: str
    diagnosis: str
    treatment: str
    notes: str | None = None


class MedicalRecordCreate(MedicalRecordBase):
    pass


class MedicalRecordUpdate(BaseModel):
    appointment_id: int | None = None
    patient_id: int | None = None
    doctor_id: int | None = None
    symptoms: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class MedicalRecordResponse(MedicalRecordBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True