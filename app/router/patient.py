from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.database import DBSessionDep
from app.models.patient import Patient
from app.models.user import User
from app.schema.patient import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
)


router = APIRouter(
    prefix="/api/patients",
    tags=["Patients"]
)


@router.post("/", response_model=PatientResponse)
async def create_patient(
    patient_data: PatientCreate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Only Super Admin and Hospital Admin
    if current_user.role_id not in [1, 2]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin or Hospital Admin can create patient profiles"
        )

    # Find target user
    result = await db.execute(
        select(User).where(User.id == patient_data.user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # User must be Patient
    if user.role_id != 8:
        raise HTTPException(
            status_code=400,
            detail="Selected user is not a Patient"
        )

    # Patient must belong to a hospital
    if user.hospital_id is None:
        raise HTTPException(
            status_code=400,
            detail="Patient must be assigned to a hospital"
        )

    # Hospital Admin can create only for own hospital
    if current_user.role_id == 2:
        if user.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can create patients only for your hospital"
            )

    # Check existing patient profile
    existing_result = await db.execute(
        select(Patient).where(
            Patient.user_id == patient_data.user_id
        )
    )

    existing_patient = existing_result.scalar_one_or_none()

    if existing_patient:
        raise HTTPException(
            status_code=400,
            detail="Patient profile already exists"
        )

    patient = Patient(
        user_id=patient_data.user_id,
        blood_group=patient_data.blood_group,
        date_of_birth=patient_data.date_of_birth,
        gender=patient_data.gender,
        address=patient_data.address,
        emergency_contact=patient_data.emergency_contact,
        is_active=True,
    )

    db.add(patient)
    await db.commit()
    await db.refresh(patient)

    return patient
@router.get("/me", response_model=PatientResponse)
async def get_my_patient_profile(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id != 8:
        raise HTTPException(
            status_code=403,
            detail="Only Patient can access this profile"
        )

    result = await db.execute(
        select(Patient).where(
            Patient.user_id == current_user.id,
            Patient.is_active == True
        )
    )

    patient = result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient profile not found"
        )

    return patient
@router.get("/", response_model=list[PatientResponse])
async def get_all_patients(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Super Admin → all active patients
    if current_user.role_id == 1:
        result = await db.execute(
            select(Patient)
            .join(User, Patient.user_id == User.id)
            .where(
                Patient.is_active == True
            )
        )

    # Hospital Admin → own hospital patients
    elif current_user.role_id == 2:
        result = await db.execute(
            select(Patient)
            .join(User, Patient.user_id == User.id)
            .where(
                Patient.is_active == True,
                User.hospital_id == current_user.hospital_id
            )
        )

    # Patient → patients in own hospital
    elif current_user.role_id == 8:
        result = await db.execute(
            select(Patient)
            .join(User, Patient.user_id == User.id)
            .where(
                Patient.is_active == True,
                User.hospital_id == current_user.hospital_id
            )
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view patients"
        )

    return result.scalars().all()
@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient_by_id(
    patient_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Patient, User.hospital_id)
        .join(User, Patient.user_id == User.id)
        .where(
            Patient.id == patient_id,
            Patient.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    patient, patient_hospital_id = row

    # Super Admin → any patient
    if current_user.role_id == 1:
        return patient

    # Hospital Admin → own hospital patients
    elif current_user.role_id == 2:
        if patient_hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can view patients only from your hospital"
            )
        return patient

    # Patient → only own profile
    elif current_user.role_id == 8:
        if patient.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can view only your own patient profile"
            )
        return patient

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view patients"
        )
@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Patient, User.hospital_id)
        .join(User, Patient.user_id == User.id)
        .where(
            Patient.id == patient_id,
            Patient.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    patient, patient_hospital_id = row

    # Super Admin → any patient
    if current_user.role_id == 1:
        pass

    # Hospital Admin → own hospital
    elif current_user.role_id == 2:
        if patient_hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can update patients only from your hospital"
            )

    # Patient → only own profile
    elif current_user.role_id == 8:
        if patient.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can update only your own patient profile"
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to update patients"
        )

    update_data = patient_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)

    return patient
@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Patient, User.hospital_id)
        .join(User, Patient.user_id == User.id)
        .where(
            Patient.id == patient_id,
            Patient.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    patient, patient_hospital_id = row

    # Super Admin → can delete any patient
    if current_user.role_id == 1:
        pass

    # Hospital Admin → own hospital only
    elif current_user.role_id == 2:
        if patient_hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can delete patients only from your hospital"
            )

    # Patient cannot delete profile
    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to delete patients"
        )

    # Soft delete
    patient.is_active = False

    await db.commit()

    return {
        "message": "Patient deleted successfully"
    }