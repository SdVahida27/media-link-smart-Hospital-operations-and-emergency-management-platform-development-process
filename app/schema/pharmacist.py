from pydantic import BaseModel


class PharmacistBase(BaseModel):
    qualification: str | None = None
    experience_years: int | None = None
    license_number: str | None = None


class PharmacistCreate(PharmacistBase):
    user_id: int


class PharmacistUpdate(BaseModel):
    qualification: str | None = None
    experience_years: int | None = None
    license_number: str | None = None
    is_active: bool | None = None


class PharmacistResponse(PharmacistBase):
    id: int
    user_id: int
    is_active: bool

    class Config:
        from_attributes = True