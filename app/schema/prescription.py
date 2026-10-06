from pydantic import BaseModel


class PrescriptionBase(BaseModel):
    medical_record_id: int
    medicine_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: str | None = None


class PrescriptionCreate(PrescriptionBase):
    pass


class PrescriptionUpdate(BaseModel):
    medical_record_id: int | None = None
    medicine_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    instructions: str | None = None
    is_active: bool | None = None


class PrescriptionResponse(PrescriptionBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True