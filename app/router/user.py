from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import require_super_admin
from app.core.database import DBSessionDep
from app.core.security import hash_password
from app.models.user import User
from app.schema.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
)

router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
)


# =========================
# Create User
# =========================
@router.post(
    "/",
    response_model=UserResponse
)
async def create_user(
    user: UserCreate,
    db: DBSessionDep,
    current_user: User = Depends(require_super_admin),
):
    # Check email
    result = await db.execute(
        select(User).where(User.email == user.email)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    # Check username
    result = await db.execute(
        select(User).where(User.username == user.username)
    )

    existing_username = result.scalar_one_or_none()

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    new_user = User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password),
        slug=user.slug,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        role_id=user.role_id,
        hospital_id=user.hospital_id,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# =========================
# Get All Users
# =========================
@router.get(
    "/",
    response_model=list[UserResponse]
)
async def get_all_users(
    db: DBSessionDep,
    current_user: User = Depends(require_super_admin),
):
    result = await db.execute(
        select(User)
    )

    users = result.scalars().all()

    return users


# =========================
# Get User By ID
# =========================
@router.get(
    "/{user_id}",
    response_model=UserResponse
)
async def get_user(
    user_id: int,
    db: DBSessionDep,
    current_user: User = Depends(require_super_admin),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


# =========================
# Update User
# =========================
@router.put(
    "/{user_id}",
    response_model=UserResponse
)
async def update_user(
    user_id: int,
    user: UserUpdate,
    db: DBSessionDep,
    current_user: User = Depends(require_super_admin),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    db_user = result.scalar_one_or_none()

    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    db_user.username = user.username
    db_user.first_name = user.first_name
    db_user.last_name = user.last_name
    db_user.phone = user.phone
    db_user.role_id = user.role_id
    db_user.hospital_id = user.hospital_id
    db_user.is_active = user.is_active

    await db.commit()
    await db.refresh(db_user)

    return db_user


# =========================
# Delete User
# =========================
@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: DBSessionDep,
    current_user: User = Depends(require_super_admin),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    db_user = result.scalar_one_or_none()

    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    await db.delete(db_user)
    await db.commit()

    return {
        "message": "User deleted successfully"
    }