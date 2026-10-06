from pydantic import BaseModel


class DepartmentBase(BaseModel):
    name: str
    description: str | None = None
    hospital_id: int


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(DepartmentBase):
    is_active: bool


class DepartmentResponse(DepartmentBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True 