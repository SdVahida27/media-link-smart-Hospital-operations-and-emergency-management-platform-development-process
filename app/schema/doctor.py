from pydantic import BaseModel


# ============================================================
# BASE
# ============================================================

class DoctorBase(BaseModel):
    user_id: int
    department_id: int
    specialization: str
    qualification: str
    experience: int
    consultation_fee: int


# ============================================================
# CREATE DOCTOR
# ============================================================

class DoctorCreate(DoctorBase):
    pass


# ============================================================
# UPDATE DOCTOR
#
# user_id is intentionally NOT included.
# A doctor profile must not be transferred
# to another user during update.
# ============================================================

class DoctorUpdate(BaseModel):
    department_id: int
    specialization: str
    qualification: str
    experience: int
    consultation_fee: int
    is_active: bool


# ============================================================
# RESPONSE
# ============================================================

class DoctorResponse(DoctorBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True