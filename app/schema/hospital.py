from pydantic import BaseModel, EmailStr


class HospitalBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    address: str
    city: str
    state: str
    country: str
    pincode: str
    logo: str | None = None


class HospitalCreate(HospitalBase):
    pass


class HospitalUpdate(HospitalBase):
    is_active: bool


class HospitalResponse(HospitalBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True