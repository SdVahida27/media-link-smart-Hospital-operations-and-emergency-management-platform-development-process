from pydantic import BaseModel


class BedCreate(BaseModel):
    room_id: int
    bed_number: str
    bed_type: str


class BedUpdate(BaseModel):
    bed_number: str | None = None
    bed_type: str | None = None
    status: str | None = None
    is_active: bool | None = None


class BedResponse(BaseModel):
    id: int
    room_id: int
    bed_number: str
    bed_type: str
    status: str
    is_active: bool

    class Config:
        from_attributes = True
class AvailableBedResponse(BaseModel):
    room_number: str
    room_type: str
    bed_number: str
    status: str