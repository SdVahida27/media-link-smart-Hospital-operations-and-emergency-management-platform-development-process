from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.database import DBSessionDep

from app.models.bed import Bed
from app.models.room import Room
from app.models.user import User

from app.schema.bed import (
    BedCreate,
    BedUpdate,
    BedResponse,
    AvailableBedResponse
)

router = APIRouter(
    prefix="/api/beds",
    tags=["Beds"]
)


# ============================================================
# CREATE BED
# ============================================================

@router.post("/", response_model=BedResponse)
async def create_bed(
    bed_data: BedCreate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Super Admin / Hospital Admin only
    # --------------------------------------------------------

    if current_user.role_id not in [1, 2]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin or Hospital Admin can create beds"
        )

    # --------------------------------------------------------
    # Check active room
    # --------------------------------------------------------

    result = await db.execute(
        select(Room).where(
            Room.id == bed_data.room_id,
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
                detail="You are not authorized to create bed in this room"
            )

    # --------------------------------------------------------
    # Validate bed type
    # --------------------------------------------------------

    allowed_bed_types = {
        "STANDARD",
        "ICU",
        "EMERGENCY"
    }

    if bed_data.bed_type not in allowed_bed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid bed type"
        )

    # --------------------------------------------------------
    # Check duplicate bed number inside same room
    # --------------------------------------------------------

    result = await db.execute(
        select(Bed).where(
            Bed.room_id == bed_data.room_id,
            Bed.bed_number == bed_data.bed_number,
            Bed.is_active == True
        )
    )

    existing_bed = result.scalar_one_or_none()

    if existing_bed:
        raise HTTPException(
            status_code=400,
            detail="Bed number already exists in this room"
        )

    # --------------------------------------------------------
    # Create bed
    # --------------------------------------------------------

    bed = Bed(
        room_id=bed_data.room_id,
        bed_number=bed_data.bed_number,
        bed_type=bed_data.bed_type,
        status="AVAILABLE",
        is_active=True
    )

    db.add(bed)

    await db.commit()
    await db.refresh(bed)

    return bed
# ============================================================
# GET ALL BEDS
# ============================================================

@router.get("/", response_model=list[BedResponse])
async def get_all_beds(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Super Admin → all hospitals
    # --------------------------------------------------------

    if current_user.role_id == 1:

        result = await db.execute(
            select(Bed)
            .join(Room, Bed.room_id == Room.id)
            .where(
                Bed.is_active == True,
                Room.is_active == True
            )
        )

    # --------------------------------------------------------
    # Hospital users → own hospital only
    # --------------------------------------------------------

    elif current_user.role_id in [2, 3, 4, 5]:

        if current_user.hospital_id is None:
            raise HTTPException(
                status_code=403,
                detail="User is not associated with a hospital"
            )

        result = await db.execute(
            select(Bed)
            .join(Room, Bed.room_id == Room.id)
            .where(
                Bed.is_active == True,
                Room.is_active == True,
                Room.hospital_id == current_user.hospital_id
            )
        )

    # --------------------------------------------------------
    # Patient should NOT use this endpoint
    # --------------------------------------------------------

    elif current_user.role_id == 8:

        raise HTTPException(
            status_code=403,
            detail="Patients can only view available beds"
        )

    else:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view beds"
        )

    return result.scalars().all()
# ============================================================
# GET AVAILABLE BEDS
# ============================================================

@router.get("/available", response_model=list[AvailableBedResponse])
async def get_available_beds(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Allowed roles
    # Patient + Hospital users
    # --------------------------------------------------------

    if current_user.role_id not in [1, 2, 3, 4, 5, 8]:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view available beds"
        )

    # --------------------------------------------------------
    # Super Admin → all hospitals
    # --------------------------------------------------------

    if current_user.role_id == 1:

        result = await db.execute(
            select(
                Room.room_number,
                Room.room_type,
                Bed.bed_number,
                Bed.status
            )
            .join(Bed, Bed.room_id == Room.id)
            .where(
                Room.is_active == True,
                Bed.is_active == True,
                Bed.status == "AVAILABLE"
            )
        )

    # --------------------------------------------------------
    # Hospital users / Patient → own hospital only
    # --------------------------------------------------------

    else:

        if current_user.hospital_id is None:
            raise HTTPException(
                status_code=403,
                detail="User is not associated with a hospital"
            )

        result = await db.execute(
            select(
                Room.room_number,
                Room.room_type,
                Bed.bed_number,
                Bed.status
            )
            .join(Bed, Bed.room_id == Room.id)
            .where(
                Room.is_active == True,
                Bed.is_active == True,
                Bed.status == "AVAILABLE",
                Room.hospital_id == current_user.hospital_id
            )
        )

    rows = result.all()

    return [
        AvailableBedResponse(
            room_number=row.room_number,
            room_type=row.room_type,
            bed_number=row.bed_number,
            status=row.status
        )
        for row in rows
    ]
# ============================================================
# GET BED BY ID
# ============================================================

@router.get("/{bed_id}", response_model=BedResponse)
async def get_bed_by_id(
    bed_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Get active bed + room
    # --------------------------------------------------------

    result = await db.execute(
        select(Bed, Room.hospital_id)
        .join(Room, Bed.room_id == Room.id)
        .where(
            Bed.id == bed_id,
            Bed.is_active == True,
            Room.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Active bed not found"
        )

    bed, hospital_id = row

    # --------------------------------------------------------
    # Super Admin
    # --------------------------------------------------------

    if current_user.role_id == 1:
        return bed

    # --------------------------------------------------------
    # Patient → use /available instead
    # --------------------------------------------------------

    if current_user.role_id == 8:
        raise HTTPException(
            status_code=403,
            detail="Patients can only view available beds"
        )

    # --------------------------------------------------------
    # Hospital users
    # --------------------------------------------------------

    if current_user.role_id in [2, 3, 4, 5]:

        if current_user.hospital_id != hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this bed"
            )

        return bed

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to view beds"
    )
# ============================================================
# UPDATE BED
# ============================================================

@router.patch("/{bed_id}", response_model=BedResponse)
async def update_bed(
    bed_id: int,
    bed_data: BedUpdate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Allowed roles
    # --------------------------------------------------------

    if current_user.role_id not in [1, 2, 4]:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to update beds"
        )

    # --------------------------------------------------------
    # Get bed + hospital
    # --------------------------------------------------------

    result = await db.execute(
        select(Bed, Room.hospital_id)
        .join(Room, Bed.room_id == Room.id)
        .where(
            Bed.id == bed_id,
            Bed.is_active == True,
            Room.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Active bed not found"
        )

    bed, hospital_id = row

    # --------------------------------------------------------
    # Hospital scope
    # --------------------------------------------------------

    if current_user.role_id in [2, 4]:

        if current_user.hospital_id != hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to update this bed"
            )

    # --------------------------------------------------------
    # Nurse → status only
    # --------------------------------------------------------

    if current_user.role_id == 4:

        if bed_data.bed_number is not None:
            raise HTTPException(
                status_code=403,
                detail="Nurse can update only bed status"
            )

        if bed_data.bed_type is not None:
            raise HTTPException(
                status_code=403,
                detail="Nurse can update only bed status"
            )

        if bed_data.is_active is not None:
            raise HTTPException(
                status_code=403,
                detail="Nurse cannot change bed active status"
            )

    # --------------------------------------------------------
    # Validate status
    # --------------------------------------------------------

    allowed_statuses = {
        "AVAILABLE",
        "OCCUPIED",
        "MAINTENANCE"
    }

    if (
        bed_data.status is not None
        and bed_data.status not in allowed_statuses
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid bed status"
        )

    # --------------------------------------------------------
    # Validate bed type
    # --------------------------------------------------------

    allowed_bed_types = {
        "STANDARD",
        "ICU",
        "EMERGENCY"
    }

    if (
        bed_data.bed_type is not None
        and bed_data.bed_type not in allowed_bed_types
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid bed type"
        )

    # --------------------------------------------------------
    # Duplicate bed number
    # --------------------------------------------------------

    if bed_data.bed_number is not None:

        duplicate_result = await db.execute(
            select(Bed).where(
                Bed.room_id == bed.room_id,
                Bed.bed_number == bed_data.bed_number,
                Bed.id != bed.id,
                Bed.is_active == True
            )
        )

        duplicate_bed = duplicate_result.scalar_one_or_none()

        if duplicate_bed:
            raise HTTPException(
                status_code=400,
                detail="Bed number already exists in this room"
            )

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    update_data = bed_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(bed, field, value)

    await db.commit()
    await db.refresh(bed)

    return bed
# ============================================================
# DELETE BED
# ============================================================

@router.delete("/{bed_id}")
async def delete_bed(
    bed_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Only Super Admin / Hospital Admin
    # --------------------------------------------------------

    if current_user.role_id not in [1, 2]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin or Hospital Admin can delete beds"
        )

    # --------------------------------------------------------
    # Get active bed + hospital
    # --------------------------------------------------------

    result = await db.execute(
        select(Bed, Room.hospital_id)
        .join(Room, Bed.room_id == Room.id)
        .where(
            Bed.id == bed_id,
            Bed.is_active == True,
            Room.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Active bed not found"
        )

    bed, hospital_id = row

    # --------------------------------------------------------
    # Hospital Admin → own hospital
    # --------------------------------------------------------

    if current_user.role_id == 2:

        if current_user.hospital_id != hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to delete this bed"
            )

    # --------------------------------------------------------
    # Prevent deleting occupied bed
    # --------------------------------------------------------

    if bed.status == "OCCUPIED":
        raise HTTPException(
            status_code=400,
            detail="Occupied bed cannot be deleted"
        )

    # --------------------------------------------------------
    # Soft delete
    # --------------------------------------------------------

    bed.is_active = False

    await db.commit()

    return {
        "message": "Bed deleted successfully"
    }