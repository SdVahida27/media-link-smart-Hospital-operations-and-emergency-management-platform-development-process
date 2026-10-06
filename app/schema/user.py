from pydantic import BaseModel, EmailStr


# =========================
# Base Schema
# =========================
class UserBase(BaseModel):
    username: str
    email: EmailStr
    slug: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    role_id: int
    hospital_id: int | None = None


# =========================
# Create User
# =========================
class UserCreate(UserBase):
    password: str


# =========================
# Update User
# =========================
class UserUpdate(BaseModel):
    username: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    role_id: int
    hospital_id: int | None = None
    is_active: bool


# =========================
# Response Schema
# =========================
class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    slug: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    role_id: int
    hospital_id: int | None = None
    is_active: bool

    class Config:
        from_attributes = True