from pydantic import BaseModel


class MedicineBase(BaseModel):
    hospital_id: int
    medicine_name: str
    generic_name: str | None = None
    category: str | None = None
    manufacturer: str | None = None
    unit: str
    quantity: int = 0
    reorder_level: int = 10


class MedicineCreate(MedicineBase):
    pass


class MedicineUpdate(BaseModel):
    medicine_name: str | None = None
    generic_name: str | None = None
    category: str | None = None
    manufacturer: str | None = None
    unit: str | None = None
    quantity: int | None = None
    reorder_level: int | None = None


class MedicineResponse(MedicineBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True