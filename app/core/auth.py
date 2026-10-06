from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select

from app.core.database import DBSessionDep
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: DBSessionDep = None,
):
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    email = payload.get("sub")

    result = await db.execute(
        select(User).where(User.email == email)
    )

    current_user = result.scalar_one_or_none()

    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return current_user

async def require_super_admin(
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id != 1:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can access this resource"
        )
    return current_user


async def require_hospital_admin(
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id != 2:
        raise HTTPException(
            status_code=403,
            detail="Only Hospital Admin can access this resource"
        )
    return current_user


async def require_doctor(
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id != 3:
        raise HTTPException(
            status_code=403,
            detail="Only Doctor can access this resource"
        )
    return current_user
async def require_nurse(
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id != 4:
        raise HTTPException(
            status_code=403,
            detail="Only Nurse can access this resource"
        )

    return current_user


async def require_patient(
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id != 8:
        raise HTTPException(
            status_code=403,
            detail="Only Patient can access this resource"
        )
    return current_user
async def require_doctor_or_hospital_admin(
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id not in [2, 3]:
        raise HTTPException(
            status_code=403,
            detail="Only Doctor or Hospital Admin can access this resource"
        )

    return current_user
async def require_medical_record_viewer(
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id not in [1, 2, 3, 4]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin, Hospital Admin, Doctor, or Nurse can access medical records",
        )

    return current_user
async def require_prescription_viewer(
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id not in [1, 2, 3, 4, 7, 8]:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access prescriptions",
        )

    return current_user