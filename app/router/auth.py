from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from app.core.auth import (
    get_current_user,
    require_super_admin,
    require_hospital_admin,
    require_doctor,
    require_patient,
)
from app.schema.user import UserResponse
from fastapi.security import OAuth2PasswordRequestForm



from app.core.database import DBSessionDep
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.models.user import User
from app.schema.auth import (
    RegisterRequest,
    TokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)



# Register
@router.post("/register")
async def register(
    user: RegisterRequest,
    db: DBSessionDep
):
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user.email)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
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

    return {
        "message": "User registered successfully",
        "user_id": new_user.id
    }


# Login
@router.post("/login", response_model=TokenResponse)
async def login(
    db: DBSessionDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )

    db_user = result.scalar_one_or_none()

    if db_user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        form_data.password,
        db_user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={"sub": db_user.email}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )
# Current Logged-in User
@router.get(
    "/me",
    response_model=UserResponse
)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user
@router.put("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Verify old password
    if not verify_password(
        request.old_password,
        current_user.password
    ):
        raise HTTPException(
            status_code=400,
            detail="Old password is incorrect"
        )

    # Hash new password
    current_user.password = hash_password(
        request.new_password
    )

    await db.commit()

    return {
        "message": "Password changed successfully"
    }
@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: DBSessionDep,
):
    result = await db.execute(
        select(User).where(User.email == request.email)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Email not found"
        )

    reset_token = create_access_token(
        data={
            "sub": user.email,
            "purpose": "reset_password"
        }
    )

    return {
        "message": "Reset token generated successfully",
        "reset_token": reset_token
    }
@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: DBSessionDep,
):
    payload = decode_access_token(request.token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    if payload.get("purpose") != "reset_password":
        raise HTTPException(
            status_code=401,
            detail="Invalid reset token"
        )

    email = payload.get("sub")

    result = await db.execute(
        select(User).where(User.email == email)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.password = hash_password(
        request.new_password
    )

    await db.commit()

    return {
        "message": "Password reset successfully"
    }
@router.get("/super-admin")
async def super_admin_dashboard(
    current_user: User = Depends(require_super_admin)
):
    return {
        "message": "Welcome Super Admin",
        "username": current_user.username
    }


@router.get("/hospital-admin")
async def hospital_admin_dashboard(
    current_user: User = Depends(require_hospital_admin)
):
    return {
        "message": "Welcome Hospital Admin",
        "username": current_user.username
    }


@router.get("/doctor")
async def doctor_dashboard(
    current_user: User = Depends(require_doctor)
):
    return {
        "message": "Welcome Doctor",
        "username": current_user.username
    }


@router.get("/patient")
async def patient_dashboard(
    current_user: User = Depends(require_patient)
):
    return {
        "message": "Welcome Patient",
        "username": current_user.username
    }
    
