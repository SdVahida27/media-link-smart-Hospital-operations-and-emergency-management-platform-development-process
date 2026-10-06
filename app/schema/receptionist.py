from pydantic import BaseModel


class ReceptionistBase(BaseModel):
    qualification: str | None = None
    experience_years: int | None = None


class ReceptionistCreate(ReceptionistBase):
    user_id: int


class ReceptionistUpdate(BaseModel):
    qualification: str | None = None
    experience_years: int | None = None
    is_active: bool | None = None


class ReceptionistResponse(ReceptionistBase):
    id: int
    user_id: int
    is_active: bool

    class Config:
        from_attributes = True