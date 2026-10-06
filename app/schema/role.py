from pydantic import BaseModel


class RoleBase(BaseModel):
    name: str
    description: str | None = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(RoleBase):
    is_active: bool


class RoleResponse(RoleBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True