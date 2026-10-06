from pydantic import BaseModel


class RoomCreate(BaseModel):
    hospital_id: int
    room_number: str
    room_type: str
    floor_number: int | None = None


class RoomUpdate(BaseModel):
    room_number: str | None = None
    room_type: str | None = None
    floor_number: int | None = None
    is_active: bool | None = None


class RoomResponse(BaseModel):
    id: int
    hospital_id: int
    room_number: str
    room_type: str
    floor_number: int | None
    is_active: bool

    class Config:
        from_attributes = True