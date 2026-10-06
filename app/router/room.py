from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.database import DBSessionDep

from app.models.hospital import Hospital
from app.models.room import Room
from app.models.user import User

from app.schema.room import (
    RoomCreate,
    RoomUpdate,
    RoomResponse
)


router = APIRouter(
    prefix="/api/rooms",
    tags=["Rooms"]
)


# ============================================================
# CREATE ROOM
# ============================================================

@router.post("/", response_model=RoomResponse)
async def create_room(
    room_data: RoomCreate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # Super Admin / Hospital Admin only
    if current_user.role_id not in [1, 2]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin or Hospital Admin can create rooms"
        )

    # --------------------------------------------------------
    # Check hospital
    # --------------------------------------------------------

    result = await db.execute(
        select(Hospital).where(
            Hospital.id == room_data.hospital_id
        )
    )

    hospital = result.scalar_one_or_none()

    if hospital is None:
        raise HTTPException(
            status_code=404,
            detail="Hospital not found"
        )

    # --------------------------------------------------------
    # Hospital Admin → own hospital only
    # --------------------------------------------------------

    if current_user.role_id == 2:

        if current_user.hospital_id != room_data.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to create room in this hospital"
            )

    # --------------------------------------------------------
    # Validate room type
    # --------------------------------------------------------

    allowed_room_types = {
        "GENERAL",
        "SEMI_PRIVATE",
        "PRIVATE",
        "ICU",
        "EMERGENCY"
    }

    if room_data.room_type not in allowed_room_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid room type"
        )

    # --------------------------------------------------------
    # Duplicate room number
    # --------------------------------------------------------

    existing_result = await db.execute(
        select(Room).where(
            Room.hospital_id == room_data.hospital_id,
            Room.room_number == room_data.room_number,
            Room.is_active == True
        )
    )

    existing_room = existing_result.scalar_one_or_none()

    if existing_room:
        raise HTTPException(
            status_code=400,
            detail="Room number already exists in this hospital"
        )

    # --------------------------------------------------------
    # Create room
    # --------------------------------------------------------

    room = Room(
        hospital_id=room_data.hospital_id,
        room_number=room_data.room_number,
        room_type=room_data.room_type,
        floor_number=room_data.floor_number,
        is_active=True
    )

    db.add(room)

    await db.commit()
    await db.refresh(room)

    return room
# ============================================================
# GET ALL ROOMS
# ============================================================

@router.get("/", response_model=list[RoomResponse])
async def get_all_rooms(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Super Admin
    # --------------------------------------------------------

    if current_user.role_id == 1:

        result = await db.execute(
            select(Room).where(
                Room.is_active == True
            )
        )

    # --------------------------------------------------------
    # Hospital users
    # --------------------------------------------------------

    elif current_user.role_id in [2, 3, 4, 5, 8]:

        result = await db.execute(
            select(Room).where(
                Room.is_active == True,
                Room.hospital_id == current_user.hospital_id
            )
        )

    else:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view rooms"
        )

    return result.scalars().all()
# ============================================================
# GET ROOM BY ID
# ============================================================

@router.get("/{room_id}", response_model=RoomResponse)
async def get_room_by_id(
    room_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    result = await db.execute(
        select(Room).where(
            Room.id == room_id,
            Room.is_active == True
        )
    )

    room = result.scalar_one_or_none()

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Active room not found"
        )

    # --------------------------------------------------------
    # Super Admin
    # --------------------------------------------------------

    if current_user.role_id == 1:
        return room

    # --------------------------------------------------------
    # Hospital based access
    # --------------------------------------------------------

    allowed_roles = [2, 3, 4, 5, 8]

    if current_user.role_id in allowed_roles:

        if current_user.hospital_id != room.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this room"
            )

        return room

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to view rooms"
    )
# ============================================================
# UPDATE ROOM
# ============================================================

@router.patch("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: int,
    room_data: RoomUpdate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Only Super Admin / Hospital Admin
    # --------------------------------------------------------

    if current_user.role_id not in [1, 2]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin or Hospital Admin can update rooms"
        )

    # --------------------------------------------------------
    # Get active room
    # --------------------------------------------------------

    result = await db.execute(
        select(Room).where(
            Room.id == room_id,
            Room.is_active == True
        )
    )

    room = result.scalar_one_or_none()

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Active room not found"
        )

    # --------------------------------------------------------
    # Hospital Admin → own hospital
    # --------------------------------------------------------

    if current_user.role_id == 2:

        if room.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to update this room"
            )

    # --------------------------------------------------------
    # Validate room type
    # --------------------------------------------------------

    allowed_room_types = {
        "GENERAL",
        "SEMI_PRIVATE",
        "PRIVATE",
        "ICU",
        "EMERGENCY"
    }

    if (
        room_data.room_type is not None
        and room_data.room_type not in allowed_room_types
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid room type"
        )

    # --------------------------------------------------------
    # Check duplicate room number
    # --------------------------------------------------------

    if room_data.room_number is not None:

        duplicate_result = await db.execute(
            select(Room).where(
                Room.hospital_id == room.hospital_id,
                Room.room_number == room_data.room_number,
                Room.id != room.id,
                Room.is_active == True
            )
        )

        duplicate_room = duplicate_result.scalar_one_or_none()

        if duplicate_room:
            raise HTTPException(
                status_code=400,
                detail="Room number already exists in this hospital"
            )

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    update_data = room_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(room, field, value)

    await db.commit()
    await db.refresh(room)

    return room
# ============================================================
# UPDATE ROOM
# ============================================================

@router.patch("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: int,
    room_data: RoomUpdate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Only Super Admin / Hospital Admin
    # --------------------------------------------------------

    if current_user.role_id not in [1, 2]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin or Hospital Admin can update rooms"
        )

    # --------------------------------------------------------
    # Get active room
    # --------------------------------------------------------

    result = await db.execute(
        select(Room).where(
            Room.id == room_id,
            Room.is_active == True
        )
    )

    room = result.scalar_one_or_none()

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Active room not found"
        )

    # --------------------------------------------------------
    # Hospital Admin → own hospital
    # --------------------------------------------------------

    if current_user.role_id == 2:

        if room.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to update this room"
            )

    # --------------------------------------------------------
    # Validate room type
    # --------------------------------------------------------

    allowed_room_types = {
        "GENERAL",
        "SEMI_PRIVATE",
        "PRIVATE",
        "ICU",
        "EMERGENCY"
    }

    if (
        room_data.room_type is not None
        and room_data.room_type not in allowed_room_types
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid room type"
        )

    # --------------------------------------------------------
    # Check duplicate room number
    # --------------------------------------------------------

    if room_data.room_number is not None:

        duplicate_result = await db.execute(
            select(Room).where(
                Room.hospital_id == room.hospital_id,
                Room.room_number == room_data.room_number,
                Room.id != room.id,
                Room.is_active == True
            )
        )

        duplicate_room = duplicate_result.scalar_one_or_none()

        if duplicate_room:
            raise HTTPException(
                status_code=400,
                detail="Room number already exists in this hospital"
            )

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    update_data = room_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(room, field, value)

    await db.commit()
    await db.refresh(room)

    return room
# ============================================================
# DELETE ROOM
# ============================================================

@router.delete("/{room_id}")
async def delete_room(
    room_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Only Super Admin / Hospital Admin
    # --------------------------------------------------------

    if current_user.role_id not in [1, 2]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin or Hospital Admin can delete rooms"
        )

    # --------------------------------------------------------
    # Get active room
    # --------------------------------------------------------

    result = await db.execute(
        select(Room).where(
            Room.id == room_id,
            Room.is_active == True
        )
    )

    room = result.scalar_one_or_none()

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Active room not found"
        )

    # --------------------------------------------------------
    # Hospital Admin → own hospital only
    # --------------------------------------------------------

    if current_user.role_id == 2:

        if room.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to delete this room"
            )

    # --------------------------------------------------------
    # Soft delete
    # --------------------------------------------------------

    room.is_active = False

    await db.commit()

    return {
        "message": "Room deleted successfully"
    }