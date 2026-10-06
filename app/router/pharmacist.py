
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.database import DBSessionDep
from app.models.pharmacist import Pharmacist
from app.models.user import User
from app.schema.pharmacist import (
    PharmacistCreate,
    PharmacistUpdate,
    PharmacistResponse,
)

router = APIRouter(
    prefix="/api/pharmacists",
    tags=["Pharmacists"]
)


# ============================================================
# CREATE PHARMACIST
#
# Super Admin -> Can create pharmacist for any hospital
# Hospital Admin -> Can create pharmacist only in own hospital
# Other roles -> Not allowed
# ============================================================

@router.post(
    "/",
    response_model=PharmacistResponse
)
async def create_pharmacist(
    request: PharmacistCreate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # ROLE CHECK
    # ========================================================

    if current_user.role_id not in [1, 2]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin or Hospital Admin can create pharmacists"
        )

    # ========================================================
    # CHECK USER
    # ========================================================

    result = await db.execute(
        select(User).where(
            User.id == request.user_id
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # ========================================================
    # USER MUST BE PHARMACIST
    # ========================================================

    if user.role_id != 7:
        raise HTTPException(
            status_code=400,
            detail="Selected user is not a pharmacist"
        )

    # ========================================================
    # USER MUST HAVE HOSPITAL
    # ========================================================

    if user.hospital_id is None:
        raise HTTPException(
            status_code=400,
            detail="Pharmacist must be assigned to a hospital"
        )

    # ========================================================
    # HOSPITAL ADMIN OWNERSHIP CHECK
    # ========================================================

    if current_user.role_id == 2:

        if user.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="Pharmacist does not belong to your hospital"
            )

    # ========================================================
    # CHECK EXISTING PHARMACIST PROFILE
    # ========================================================

    result = await db.execute(
        select(Pharmacist).where(
            Pharmacist.user_id == request.user_id
        )
    )

    existing_pharmacist = result.scalar_one_or_none()

    if existing_pharmacist is not None:
        raise HTTPException(
            status_code=400,
            detail="Pharmacist profile already exists"
        )

    # ========================================================
    # CHECK LICENSE NUMBER
    # ========================================================

    if request.license_number:

        result = await db.execute(
            select(Pharmacist).where(
                Pharmacist.license_number == request.license_number
            )
        )

        existing_license = result.scalar_one_or_none()

        if existing_license is not None:
            raise HTTPException(
                status_code=400,
                detail="License number already exists"
            )

    # ========================================================
    # CREATE PHARMACIST
    # ========================================================

    pharmacist = Pharmacist(
        user_id=request.user_id,
        qualification=request.qualification,
        experience_years=request.experience_years,
        license_number=request.license_number,
        is_active=True,
    )

    db.add(pharmacist)

    await db.commit()
    await db.refresh(pharmacist)

    return pharmacist
# ============================================================
# GET MY PHARMACIST PROFILE
#
# Only logged-in Pharmacist can access
# ============================================================

@router.get(
    "/me",
    response_model=PharmacistResponse
)
async def get_my_pharmacist_profile(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # ROLE CHECK
    # ========================================================

    if current_user.role_id != 7:
        raise HTTPException(
            status_code=403,
            detail="Only Pharmacist can access this profile"
        )

    # ========================================================
    # GET PHARMACIST PROFILE
    # ========================================================

    result = await db.execute(
        select(Pharmacist).where(
            Pharmacist.user_id == current_user.id
        )
    )

    pharmacist = result.scalar_one_or_none()

    if pharmacist is None:
        raise HTTPException(
            status_code=404,
            detail="Pharmacist profile not found"
        )

    # ========================================================
    # ACTIVE CHECK
    # ========================================================

    if not pharmacist.is_active:
        raise HTTPException(
            status_code=404,
            detail="Pharmacist profile not found"
        )

    return pharmacist
@router.get("/me", response_model=PharmacistResponse)
async def get_my_pharmacist_profile(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id != 7:
        raise HTTPException(
            status_code=403,
            detail="Only Pharmacist can access this profile"
        )

    result = await db.execute(
        select(Pharmacist).where(
            Pharmacist.user_id == current_user.id
        )
    )

    pharmacist = result.scalar_one_or_none()

    if pharmacist is None:
        raise HTTPException(
            status_code=404,
            detail="Pharmacist profile not found"
        )

    if not pharmacist.is_active:
        raise HTTPException(
            status_code=404,
            detail="Pharmacist profile not found"
        )

    return pharmacist
@router.get("/", response_model=list[PharmacistResponse])
async def get_all_pharmacists(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Super Admin
    if current_user.role_id == 1:
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.id)
            .where(
                Pharmacist.is_active == True
            )
        )

    # Hospital Admin / Pharmacist
    elif current_user.role_id in [2, 7]:
        result = await db.execute(
            select(Pharmacist)
            .join(User, Pharmacist.user_id == User.id)
            .where(
                Pharmacist.is_active == True,
                User.hospital_id == current_user.hospital_id
            )
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view pharmacists"
        )

    return result.scalars().all()
@router.get("/{pharmacist_id}", response_model=PharmacistResponse)
async def get_pharmacist_by_id(
    pharmacist_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Pharmacist, User.hospital_id)
        .join(User, Pharmacist.user_id == User.id)
        .where(
            Pharmacist.id == pharmacist_id,
            Pharmacist.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Pharmacist not found"
        )

    pharmacist, pharmacist_hospital_id = row

    # Super Admin
    if current_user.role_id == 1:
        return pharmacist

    # Hospital Admin / Pharmacist
    if current_user.role_id in [2, 7]:
        if pharmacist_hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this pharmacist"
            )

        return pharmacist

    # Other roles
    raise HTTPException(
        status_code=403,
        detail="You are not authorized to view pharmacists"
    )
@router.patch("/{pharmacist_id}", response_model=PharmacistResponse)
async def update_pharmacist(
    pharmacist_id: int,
    pharmacist_data: PharmacistUpdate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Pharmacist, User.hospital_id)
        .join(User, Pharmacist.user_id == User.id)
        .where(
            Pharmacist.id == pharmacist_id,
            Pharmacist.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Pharmacist not found"
        )

    pharmacist, pharmacist_hospital_id = row

    # Super Admin
    if current_user.role_id == 1:
        pass

    # Hospital Admin
    elif current_user.role_id == 2:
        if pharmacist_hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to update this pharmacist"
            )

    # Pharmacist - only own profile
    elif current_user.role_id == 7:
        if pharmacist.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can update only your own profile"
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to update pharmacists"
        )

    # Check duplicate license number
    if pharmacist_data.license_number is not None:
        license_result = await db.execute(
            select(Pharmacist).where(
                Pharmacist.license_number == pharmacist_data.license_number,
                Pharmacist.id != pharmacist_id
            )
        )

        existing_license = license_result.scalar_one_or_none()

        if existing_license:
            raise HTTPException(
                status_code=400,
                detail="License number already exists"
            )

    # Update only provided fields
    update_data = pharmacist_data.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(pharmacist, field, value)

    await db.commit()
    await db.refresh(pharmacist)

    return pharmacist
@router.delete("/{pharmacist_id}")
async def delete_pharmacist(
    pharmacist_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Pharmacist, User.hospital_id)
        .join(User, Pharmacist.user_id == User.id)
        .where(
            Pharmacist.id == pharmacist_id,
            Pharmacist.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Pharmacist not found"
        )

    pharmacist, pharmacist_hospital_id = row

    # Super Admin
    if current_user.role_id == 1:
        pass

    # Hospital Admin
    elif current_user.role_id == 2:
        if pharmacist_hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to delete this pharmacist"
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin or Hospital Admin can delete pharmacists"
        )

    pharmacist.is_active = False

    await db.commit()

    return {
        "message": "Pharmacist deleted successfully"
    }