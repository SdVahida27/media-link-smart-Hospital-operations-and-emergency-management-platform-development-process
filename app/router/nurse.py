from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import (
    get_current_user,
    require_hospital_admin,
    require_nurse,
)
from app.core.database import DBSessionDep

from app.models.nurse import Nurse
from app.models.user import User
from app.models.department import Department

from app.schema.nurse import (
    NurseCreate,
    NurseUpdate,
    NurseResponse,
)

router = APIRouter(
    prefix="/api/nurses",
    tags=["Nurses"],
)


# ============================================================
# CREATE NURSE
#
# Hospital Admin only
#
# Rules:
# 1. Logged-in user must be Hospital Admin
# 2. Selected user must exist
# 3. Selected user must have Nurse role
# 4. User must belong to Hospital Admin's hospital
# 5. Department must exist
# 6. Department must belong to same hospital
# 7. Department must be active
# 8. Nurse profile must not already exist
# ============================================================

@router.post(
    "/",
    response_model=NurseResponse
)
async def create_nurse(
    nurse: NurseCreate,
    db: DBSessionDep,
    current_user: User = Depends(
        require_hospital_admin
    ),
):

    # ========================================================
    # GET USER
    # ========================================================

    result = await db.execute(
        select(User).where(
            User.id == nurse.user_id
        )
    )

    db_user = result.scalar_one_or_none()

    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # ========================================================
    # USER MUST BE NURSE
    # role_id = 4
    # ========================================================

    if db_user.role_id != 4:
        raise HTTPException(
            status_code=400,
            detail="Selected user is not a Nurse"
        )

    # ========================================================
    # USER HOSPITAL CHECK
    # ========================================================

    if db_user.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only create nurses for your hospital"
        )

    # ========================================================
    # GET DEPARTMENT
    # ========================================================

    result = await db.execute(
        select(Department).where(
            Department.id == nurse.department_id
        )
    )

    department = result.scalar_one_or_none()

    if department is None:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # ========================================================
    # DEPARTMENT HOSPITAL CHECK
    # ========================================================

    if department.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only assign nurses to departments from your hospital"
        )

    # ========================================================
    # DEPARTMENT ACTIVE CHECK
    # ========================================================

    if not department.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot assign nurse to an inactive department"
        )

    # ========================================================
    # CHECK DUPLICATE NURSE PROFILE
    # ========================================================

    result = await db.execute(
        select(Nurse).where(
            Nurse.user_id == nurse.user_id
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Nurse profile already exists"
        )

    # ========================================================
    # CREATE NURSE
    # ========================================================

    new_nurse = Nurse(
        user_id=nurse.user_id,
        department_id=nurse.department_id,
        qualification=nurse.qualification,
        experience=nurse.experience,
        is_active=True,
    )

    db.add(new_nurse)

    # ========================================================
    # SAVE TO DATABASE
    # ========================================================

    await db.commit()

    await db.refresh(new_nurse)

    return new_nurse


# ============================================================
# GET MY NURSE PROFILE
#
# Nurse only
#
# IMPORTANT:
# This route MUST come before /{nurse_id}
# ============================================================

@router.get(
    "/my-profile"
)
async def get_my_nurse_profile(
    db: DBSessionDep,
    current_user: User = Depends(
        require_nurse
    ),
):

    # ========================================================
    # GET NURSE PROFILE
    # ========================================================

    result = await db.execute(
        select(Nurse).where(
            Nurse.user_id == current_user.id
        )
    )

    nurse = result.scalar_one_or_none()

    if nurse is None:
        raise HTTPException(
            status_code=404,
            detail="Nurse profile not found"
        )

    # ========================================================
    # RETURN PROFILE
    # ========================================================

    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "nurse_id": nurse.id,
        "hospital_id": current_user.hospital_id
    }
# ============================================================
# GET NURSE BY ID
#
# Super Admin + Hospital Admin + Doctor + Nurse
#
# Hospital restriction:
# 1. Super Admin → Can view any nurse
# 2. Hospital Admin → Only nurses from own hospital
# 3. Doctor → Only nurses from own hospital
# 4. Nurse → Only nurses from own hospital
# 5. Other roles → Not allowed
# ============================================================

@router.get(
    "/{nurse_id}",
    response_model=NurseResponse
)
async def get_nurse(
    nurse_id: int,
    db: DBSessionDep,
    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # ROLE CHECK
    # ========================================================

    if current_user.role_id not in [1, 2, 3, 4]:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access nurses"
        )

    # ========================================================
    # GET NURSE
    # ========================================================

    result = await db.execute(
        select(Nurse).where(
            Nurse.id == nurse_id
        )
    )

    nurse = result.scalar_one_or_none()

    if nurse is None:
        raise HTTPException(
            status_code=404,
            detail="Nurse not found"
        )

    # ========================================================
    # SUPER ADMIN
    #
    # Can view any nurse
    # ========================================================

    if current_user.role_id == 1:
        return nurse

    # ========================================================
    # GET NURSE USER
    # ========================================================

    user_result = await db.execute(
        select(User).where(
            User.id == nurse.user_id
        )
    )

    nurse_user = user_result.scalar_one_or_none()

    if nurse_user is None:
        raise HTTPException(
            status_code=404,
            detail="Nurse user not found"
        )

    # ========================================================
    # HOSPITAL RESTRICTION
    # ========================================================

    if (
        nurse_user.hospital_id
        != current_user.hospital_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only access nurses from your hospital"
        )

    return nurse
# ============================================================
# GET ALL NURSES
#
# Super Admin + Hospital Admin + Doctor + Nurse
#
# Only ACTIVE nurses are returned
#
# Hospital restriction:
# 1. Super Admin → Active nurses from all hospitals
# 2. Hospital Admin → Active nurses from own hospital
# 3. Doctor → Active nurses from own hospital
# 4. Nurse → Active nurses from own hospital
# ============================================================

@router.get(
    "/",
    response_model=list[NurseResponse]
)
async def get_all_nurses(
    db: DBSessionDep,
    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # CHECK ROLE
    # ========================================================

    if current_user.role_id not in [1, 2, 3, 4]:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access nurses"
        )

    # ========================================================
    # SUPER ADMIN
    #
    # All hospitals
    # Active nurses only
    # ========================================================

    if current_user.role_id == 1:

        result = await db.execute(
            select(Nurse).where(
                Nurse.is_active == True
            )
        )

    # ========================================================
    # HOSPITAL USERS
    #
    # Hospital Admin / Doctor / Nurse
    # Own hospital only
    # Active nurses only
    # ========================================================

    else:

        result = await db.execute(
            select(Nurse)
            .join(
                User,
                Nurse.user_id == User.id
            )
            .where(
                User.hospital_id
                == current_user.hospital_id,
                Nurse.is_active == True
            )
        )

    nurses = result.scalars().all()

    return nurses
# ============================================================
# UPDATE NURSE
#
# Hospital Admin only
# ============================================================

@router.put(
    "/{nurse_id}",
    response_model=NurseResponse
)
async def update_nurse(
    nurse_id: int,
    request: NurseUpdate,
    db: DBSessionDep,
    current_user: User = Depends(
        require_hospital_admin
    ),
):

    # --------------------------------------------------------
    # Get Nurse
    # --------------------------------------------------------

    result = await db.execute(
        select(Nurse).where(
            Nurse.id == nurse_id
        )
    )

    nurse = result.scalar_one_or_none()

    if nurse is None:
        raise HTTPException(
            status_code=404,
            detail="Nurse not found"
        )

    # --------------------------------------------------------
    # Get Nurse User
    # --------------------------------------------------------

    user_result = await db.execute(
        select(User).where(
            User.id == nurse.user_id
        )
    )

    nurse_user = user_result.scalar_one_or_none()

    if nurse_user is None:
        raise HTTPException(
            status_code=404,
            detail="Nurse user not found"
        )

    # --------------------------------------------------------
    # Hospital Restriction
    # --------------------------------------------------------

    if nurse_user.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only update nurses from your hospital"
        )

    # --------------------------------------------------------
    # Get Department
    # --------------------------------------------------------

    department_result = await db.execute(
        select(Department).where(
            Department.id == request.department_id
        )
    )

    department = department_result.scalar_one_or_none()

    if department is None:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # --------------------------------------------------------
    # Department Hospital Check
    # --------------------------------------------------------

    if department.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only assign nurses to departments from your hospital"
        )

    # --------------------------------------------------------
    # Department Active Check
    # --------------------------------------------------------

    if not department.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot assign nurse to an inactive department"
        )

    # --------------------------------------------------------
    # Update Nurse
    # --------------------------------------------------------

    nurse.department_id = request.department_id
    nurse.qualification = request.qualification
    nurse.experience = request.experience
    nurse.is_active = request.is_active

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    await db.commit()

    await db.refresh(nurse)

    return nurse
# ============================================================
# DELETE NURSE
#
# Hospital Admin only
#
# Soft Delete:
# Nurse record will NOT be removed from database.
# is_active will be changed to False.
# ============================================================

@router.delete(
    "/{nurse_id}"
)
async def delete_nurse(
    nurse_id: int,
    db: DBSessionDep,
    current_user: User = Depends(
        require_hospital_admin
    ),
):

    # ========================================================
    # GET NURSE
    # ========================================================

    result = await db.execute(
        select(Nurse).where(
            Nurse.id == nurse_id
        )
    )

    nurse = result.scalar_one_or_none()

    if nurse is None:
        raise HTTPException(
            status_code=404,
            detail="Nurse not found"
        )

    # ========================================================
    # GET NURSE USER
    # ========================================================

    user_result = await db.execute(
        select(User).where(
            User.id == nurse.user_id
        )
    )

    nurse_user = user_result.scalar_one_or_none()

    if nurse_user is None:
        raise HTTPException(
            status_code=404,
            detail="Nurse user not found"
        )

    # ========================================================
    # HOSPITAL RESTRICTION
    # ========================================================

    if nurse_user.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete nurses from your hospital"
        )

    # ========================================================
    # CHECK ALREADY INACTIVE
    # ========================================================

    if not nurse.is_active:
        raise HTTPException(
            status_code=400,
            detail="Nurse is already inactive"
        )

    # ========================================================
    # SOFT DELETE
    # ========================================================

    nurse.is_active = False

    # ========================================================
    # SAVE
    # ========================================================

    await db.commit()

    return {
        "message": "Nurse deleted successfully"
    }