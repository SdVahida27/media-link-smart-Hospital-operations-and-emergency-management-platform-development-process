from pydantic import BaseModel


# ============================================================
# BASE SCHEMA
# ============================================================

class NurseBase(BaseModel):
    user_id: int
    department_id: int
    qualification: str
    experience: int


# ============================================================
# CREATE NURSE
# ============================================================

class NurseCreate(NurseBase):
    pass


# ============================================================
# UPDATE NURSE
# ============================================================

class NurseUpdate(BaseModel):
    department_id: int
    qualification: str
    experience: int
    is_active: bool


# ============================================================
# RESPONSE
# ============================================================

class NurseResponse(NurseBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True