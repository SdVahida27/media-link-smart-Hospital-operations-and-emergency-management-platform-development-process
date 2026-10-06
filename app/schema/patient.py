from pydantic import BaseModel


class PatientBase(BaseModel):
    blood_group: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    address: str | None = None
    emergency_contact: str | None = None


class PatientCreate(PatientBase):
    user_id: int


class PatientUpdate(BaseModel):
    blood_group: str | None = None
    date_of_birth: str | None = None
    gender: str | None = None
    address: str | None = None
    emergency_contact: str | None = None
    is_active: bool | None = None


class PatientResponse(PatientBase):
    id: int
    user_id: int
    is_active: bool

    class Config:
        from_attributes = True