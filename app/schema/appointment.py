from datetime import date, time

from pydantic import BaseModel


class AppointmentBase(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: time
    reason: str


class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    appointment_date: date
    appointment_time: time
    reason: str
    status: str
    is_active: bool


class AppointmentResponse(AppointmentBase):
    id: int
    status: str
    is_active: bool

    class Config:
        from_attributes = True