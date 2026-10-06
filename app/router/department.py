from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select

from app.core.database import DBSessionDep
from app.core.auth import (
    require_super_admin,
     get_current_user,
    require_hospital_admin,
)
from app.models.department import Department
from app.models.user import User
from app.schema.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
)

router = APIRouter(
    prefix="/api/departments",
    tags=["Departments"]
)


# ============================================================
# CREATE DEPARTMENT
#
# Super Admin    -> Any hospital
# Hospital Admin -> Own hospital only
# ============================================================

@router.post(
    "/",
    response_model=DepartmentResponse
)
async def create_department(
    department: DepartmentCreate,
    db: DBSessionDep,
    current_user: User = Depends(
        require_hospital_admin
    ),
):

    # ========================================================
    # HOSPITAL ADMIN HOSPITAL CHECK
    # ========================================================

    if current_user.role_id == 2:

        if department.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can only create departments for your hospital"
            )

    # ========================================================
    # CHECK DUPLICATE DEPARTMENT
    # ========================================================

    result = await db.execute(
        select(Department).where(
            Department.name == department.name,
            Department.hospital_id == department.hospital_id
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Department already exists in this hospital"
        )

    # ========================================================
    # CREATE
    # ========================================================

    new_department = Department(
        name=department.name,
        description=department.description,
        hospital_id=department.hospital_id,
        is_active=True,
    )

    db.add(new_department)

    await db.commit()
    await db.refresh(new_department)

    return new_department
# ============================================================
# GET ALL DEPARTMENTS
#
# Super Admin      -> All hospitals
# Hospital Admin   -> Own hospital
# Doctor           -> Own hospital
# Nurse            -> Own hospital
# Patient          -> Own hospital
#
# Only active departments
# ============================================================

@router.get(
    "/",
    response_model=list[DepartmentResponse]
)
async def get_all_departments(
    db: DBSessionDep,
    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # SUPER ADMIN
    # ========================================================

    if current_user.role_id == 1:

        result = await db.execute(
            select(Department).where(
                Department.is_active == True
            )
        )

    # ========================================================
    # OTHER ROLES
    # ========================================================

    elif current_user.role_id in [2, 3, 4, 8]:

        result = await db.execute(
            select(Department).where(
                Department.hospital_id
                == current_user.hospital_id,
                Department.is_active == True
            )
        )

    # ========================================================
    # UNAUTHORIZED
    # ========================================================

    else:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view departments"
        )

    departments = result.scalars().all()

    return departments
# ============================================================
# GET DEPARTMENT BY ID
#
# Super Admin      -> Any hospital
# Hospital Admin   -> Own hospital
# Doctor           -> Own hospital
# Nurse            -> Own hospital
# Patient          -> Own hospital
# ============================================================

@router.get(
    "/{department_id}",
    response_model=DepartmentResponse
)
async def get_department(
    department_id: int,
    db: DBSessionDep,
    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # GET DEPARTMENT
    # ========================================================

    result = await db.execute(
        select(Department).where(
            Department.id == department_id
        )
    )

    department = result.scalar_one_or_none()

    if department is None:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # ========================================================
    # SUPER ADMIN
    # ========================================================

    if current_user.role_id == 1:
        return department

    # ========================================================
    # ALLOWED ROLES
    # ========================================================

    if current_user.role_id not in [2, 3, 4, 8]:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this department"
        )

    # ========================================================
    # HOSPITAL RESTRICTION
    # ========================================================

    if department.hospital_id != current_user.hospital_id:

        raise HTTPException(
            status_code=403,
            detail="You can only access departments from your hospital"
        )

    # ========================================================
    # ACTIVE CHECK
    # ========================================================

    if not department.is_active:

        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    return department

# Update Department
# ============================================================
# UPDATE DEPARTMENT
#
# Super Admin      -> Any hospital
# Hospital Admin   -> Own hospital only
# ============================================================

@router.put(
    "/{department_id}",
    response_model=DepartmentResponse
)
async def update_department(
    department_id: int,
    department: DepartmentUpdate,
    db: DBSessionDep,
    current_user: User = Depends(
        require_hospital_admin
    ),
):

    # ========================================================
    # GET DEPARTMENT
    # ========================================================

    result = await db.execute(
        select(Department).where(
            Department.id == department_id
        )
    )

    db_department = result.scalar_one_or_none()

    if db_department is None:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # ========================================================
    # HOSPITAL ADMIN
    # Own hospital only
    # ========================================================

    if current_user.role_id == 2:

        if db_department.hospital_id != current_user.hospital_id:

            raise HTTPException(
                status_code=403,
                detail="You can only update departments from your hospital"
            )

    # ========================================================
    # DUPLICATE NAME CHECK
    # ========================================================

    result = await db.execute(
        select(Department).where(
            Department.name == department.name,
            Department.hospital_id
            == db_department.hospital_id,
            Department.id != department_id
        )
    )

    existing = result.scalar_one_or_none()

    if existing:

        raise HTTPException(
            status_code=400,
            detail="Department already exists in this hospital"
        )

    # ========================================================
    # UPDATE
    # ========================================================

    db_department.name = department.name
    db_department.description = department.description
    db_department.is_active = department.is_active

    # IMPORTANT:
    # hospital_id is NOT updated.
    # Department stays in its original hospital.

    # ========================================================
    # SAVE
    # ========================================================

    await db.commit()

    await db.refresh(db_department)

    return db_department
# ============================================================
# DELETE DEPARTMENT
#
# Super Admin      -> Any hospital
# Hospital Admin   -> Own hospital only
#
# Soft Delete
# ============================================================

@router.delete(
    "/{department_id}"
)
async def delete_department(
    department_id: int,
    db: DBSessionDep,
    current_user: User = Depends(
        require_hospital_admin
    ),
):

    # ========================================================
    # GET DEPARTMENT
    # ========================================================

    result = await db.execute(
        select(Department).where(
            Department.id == department_id
        )
    )

    department = result.scalar_one_or_none()

    if department is None:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # ========================================================
    # HOSPITAL ADMIN
    # Own hospital only
    # ========================================================

    if current_user.role_id == 2:

        if department.hospital_id != current_user.hospital_id:

            raise HTTPException(
                status_code=403,
                detail="You can only delete departments from your hospital"
            )

    # ========================================================
    # SOFT DELETE
    # ========================================================

    department.is_active = False

    await db.commit()

    return {
        "message": "Department deleted successfully"
    }