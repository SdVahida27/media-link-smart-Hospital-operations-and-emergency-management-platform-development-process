from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.database import DBSessionDep
from app.models.receptionist import Receptionist
from app.models.user import User
from app.schema.receptionist import (
    ReceptionistCreate,
    ReceptionistUpdate,
    ReceptionistResponse
)

router = APIRouter(
    prefix="/api/receptionists",
    tags=["Receptionists"]
)


@router.post("/", response_model=ReceptionistResponse)
async def create_receptionist(
    receptionist_data: ReceptionistCreate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Only Super Admin and Hospital Admin
    if current_user.role_id not in [1, 2]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin or Hospital Admin can create receptionist profiles"
        )

    # Find target user
    result = await db.execute(
        select(User).where(User.id == receptionist_data.user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # User must be Receptionist
    if user.role_id != 5:
        raise HTTPException(
            status_code=400,
            detail="Selected user is not a Receptionist"
        )

    # Receptionist must belong to a hospital
    if user.hospital_id is None:
        raise HTTPException(
            status_code=400,
            detail="Receptionist must be assigned to a hospital"
        )

    # Hospital Admin → own hospital only
    if current_user.role_id == 2:
        if user.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can create receptionists only for your hospital"
            )

    # Check existing profile
    existing_result = await db.execute(
        select(Receptionist).where(
            Receptionist.user_id == receptionist_data.user_id
        )
    )

    existing_receptionist = existing_result.scalar_one_or_none()

    if existing_receptionist:
        raise HTTPException(
            status_code=400,
            detail="Receptionist profile already exists"
        )

    receptionist = Receptionist(
        user_id=receptionist_data.user_id,
        qualification=receptionist_data.qualification,
        experience_years=receptionist_data.experience_years,
        is_active=True,
    )

    db.add(receptionist)

    await db.commit()
    await db.refresh(receptionist)

    return receptionist
@router.get("/me", response_model=ReceptionistResponse)
async def get_my_receptionist_profile(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id != 5:
        raise HTTPException(
            status_code=403,
            detail="Only Receptionist can access this profile"
        )

    result = await db.execute(
        select(Receptionist).where(
            Receptionist.user_id == current_user.id,
            Receptionist.is_active == True
        )
    )

    receptionist = result.scalar_one_or_none()

    if receptionist is None:
        raise HTTPException(
            status_code=404,
            detail="Receptionist profile not found"
        )

    return receptionist
@router.get("/", response_model=list[ReceptionistResponse])
async def get_all_receptionists(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Super Admin → all active receptionists
    if current_user.role_id == 1:
        result = await db.execute(
            select(Receptionist)
            .join(User, Receptionist.user_id == User.id)
            .where(
                Receptionist.is_active == True
            )
        )

    # Hospital Admin → own hospital receptionists
    elif current_user.role_id == 2:
        result = await db.execute(
            select(Receptionist)
            .join(User, Receptionist.user_id == User.id)
            .where(
                Receptionist.is_active == True,
                User.hospital_id == current_user.hospital_id
            )
        )

    # Receptionist → own hospital receptionists
    elif current_user.role_id == 5:
        result = await db.execute(
            select(Receptionist)
            .join(User, Receptionist.user_id == User.id)
            .where(
                Receptionist.is_active == True,
                User.hospital_id == current_user.hospital_id
            )
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view receptionists"
        )

    return result.scalars().all()
@router.get("/{receptionist_id}", response_model=ReceptionistResponse)
async def get_receptionist(
    receptionist_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Receptionist, User.hospital_id)
        .join(User, Receptionist.user_id == User.id)
        .where(
            Receptionist.id == receptionist_id,
            Receptionist.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Receptionist not found"
        )

    receptionist, hospital_id = row

    # Super Admin → can view any receptionist
    if current_user.role_id == 1:
        return receptionist

    # Hospital Admin → only own hospital
    if current_user.role_id == 2:
        if current_user.hospital_id != hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can access only receptionists from your hospital"
            )
        return receptionist

    # Receptionist → only own profile
    if current_user.role_id == 5:
        if current_user.id != receptionist.user_id:
            raise HTTPException(
                status_code=403,
                detail="You can access only your own profile"
            )
        return receptionist

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to access receptionist details"
    )
@router.put("/{receptionist_id}", response_model=ReceptionistResponse)
async def update_receptionist(
    receptionist_id: int,
    receptionist_data: ReceptionistUpdate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Receptionist, User.hospital_id)
        .join(User, Receptionist.user_id == User.id)
        .where(
            Receptionist.id == receptionist_id,
            Receptionist.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Receptionist not found"
        )

    receptionist, hospital_id = row

    # Super Admin → can update any receptionist
    if current_user.role_id == 1:
        pass

    # Hospital Admin → own hospital only
    elif current_user.role_id == 2:
        if current_user.hospital_id != hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can update only receptionists from your hospital"
            )

    # Receptionist → own profile only
    elif current_user.role_id == 5:
        if current_user.id != receptionist.user_id:
            raise HTTPException(
                status_code=403,
                detail="You can update only your own profile"
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to update receptionist"
        )

    # Update only fields provided by the user
    update_data = receptionist_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(receptionist, field, value)

    await db.commit()
    await db.refresh(receptionist)

    return receptionist
@router.delete("/{receptionist_id}")
async def delete_receptionist(
    receptionist_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Receptionist, User.hospital_id)
        .join(User, Receptionist.user_id == User.id)
        .where(
            Receptionist.id == receptionist_id,
            Receptionist.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Receptionist not found"
        )

    receptionist, hospital_id = row

    # Super Admin
    if current_user.role_id == 1:
        pass

    # Hospital Admin → own hospital only
    elif current_user.role_id == 2:
        if current_user.hospital_id != hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can delete only receptionists from your hospital"
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin or Hospital Admin can delete receptionist"
        )

    # Soft delete
    receptionist.is_active = False

    await db.commit()

    return {
        "message": "Receptionist deleted successfully"
    }