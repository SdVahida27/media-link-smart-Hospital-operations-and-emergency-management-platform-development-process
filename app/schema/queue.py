from datetime import date

from pydantic import BaseModel


class QueueCreate(BaseModel):
    appointment_id: int


class QueueUpdate(BaseModel):
    status: str | None = None
    is_active: bool | None = None


class QueueResponse(BaseModel):
    id: int
    appointment_id: int
    patient_id: int
    doctor_id: int
    token_number: int
    queue_date: date
    status: str
    is_active: bool

    class Config:
        from_attributes = True