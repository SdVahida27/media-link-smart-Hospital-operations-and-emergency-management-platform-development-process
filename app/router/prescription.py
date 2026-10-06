from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import (
    get_current_user,
    require_doctor,
    require_prescription_viewer,
)
from app.core.database import DBSessionDep

from app.models.prescription import Prescription
from app.models.medical_record import MedicalRecord
from app.models.doctor import Doctor
from app.models.user import User

from app.schema.prescription import (
    PrescriptionCreate,
    PrescriptionUpdate,
    PrescriptionResponse,
)

router = APIRouter(
    prefix="/api/prescriptions",
    tags=["Prescriptions"],
)


# ============================================================
# CREATE PRESCRIPTION
#
# Doctor only
#
# Rules:
# 1. Logged-in user must be a Doctor
# 2. Doctor must have a Doctor profile
# 3. Medical Record must exist
# 4. Medical Record must be active
# 5. Medical Record must belong to this Doctor
# ============================================================

@router.post(
    "/",
    response_model=PrescriptionResponse
)
async def create_prescription(
    prescription: PrescriptionCreate,
    db: DBSessionDep,
    current_user: User = Depends(require_doctor),
):

    # ========================================================
    # GET DOCTOR PROFILE
    # ========================================================

    doctor_result = await db.execute(
        select(Doctor).where(
            Doctor.user_id == current_user.id
        )
    )

    doctor = doctor_result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    # ========================================================
    # GET MEDICAL RECORD
    # ========================================================

    record_result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id == prescription.medical_record_id
        )
    )

    medical_record = record_result.scalar_one_or_none()

    if medical_record is None:
        raise HTTPException(
            status_code=404,
            detail="Medical Record not found"
        )

    # ========================================================
    # CHECK MEDICAL RECORD ACTIVE
    # ========================================================

    if not medical_record.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot create prescription for an inactive medical record"
        )

    # ========================================================
    # DOCTOR OWNERSHIP CHECK
    # ========================================================

    if medical_record.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only create prescriptions for your own medical records"
        )

    # ========================================================
    # CREATE PRESCRIPTION
    # ========================================================

    new_prescription = Prescription(
        medical_record_id=medical_record.id,
        medicine_name=prescription.medicine_name,
        dosage=prescription.dosage,
        frequency=prescription.frequency,
        duration=prescription.duration,
        instructions=prescription.instructions,
        is_active=True,
    )

    db.add(new_prescription)

    # ========================================================
    # SAVE TO DATABASE
    # ========================================================

    await db.commit()

    await db.refresh(new_prescription)

    return new_prescription
# ============================================================
# GET ALL PRESCRIPTIONS
#
# Super Admin      -> All hospitals
# Hospital Admin   -> Own hospital
# Doctor           -> Own prescriptions only
# Nurse            -> Own hospital
# Pharmacist       -> Own hospital
# Patient          -> Cannot access all prescriptions
# ============================================================

@router.get(
    "/",
    response_model=list[PrescriptionResponse]
)
async def get_all_prescriptions(
    db: DBSessionDep,
    current_user: User = Depends(
        require_prescription_viewer
    ),
):

    # ========================================================
    # SUPER ADMIN
    # role_id = 1
    # ========================================================

    if current_user.role_id == 1:

        result = await db.execute(
            select(Prescription).where(
                Prescription.is_active == True
            )
        )

    # ========================================================
    # DOCTOR
    # role_id = 3
    #
    # Doctor can see ONLY his own prescriptions
    # ========================================================

    elif current_user.role_id == 3:

        # Get logged-in doctor's profile

        doctor_result = await db.execute(
            select(Doctor).where(
                Doctor.user_id == current_user.id
            )
        )

        doctor = doctor_result.scalar_one_or_none()

        if doctor is None:
            raise HTTPException(
                status_code=404,
                detail="Doctor profile not found"
            )

        # Get prescriptions belonging to
        # this doctor's medical records

        result = await db.execute(
            select(Prescription)
            .join(
                MedicalRecord,
                Prescription.medical_record_id
                == MedicalRecord.id
            )
            .where(
                MedicalRecord.doctor_id == doctor.id,
                Prescription.is_active == True
            )
        )

    # ========================================================
    # PATIENT
    # role_id = 8
    #
    # Patient cannot see all prescriptions
    # ========================================================

    elif current_user.role_id == 8:

        raise HTTPException(
            status_code=403,
            detail="Patients can only view their own prescriptions"
        )

    # ========================================================
    # HOSPITAL ADMIN / NURSE / PHARMACIST
    #
    # role_id = 2 / 4 / 7
    #
    # Only their hospital
    # ========================================================

    else:

        result = await db.execute(
            select(Prescription)
            .join(
                MedicalRecord,
                Prescription.medical_record_id
                == MedicalRecord.id
            )
            .join(
                Doctor,
                MedicalRecord.doctor_id
                == Doctor.id
            )
            .join(
                User,
                Doctor.user_id
                == User.id
            )
            .where(
                User.hospital_id
                == current_user.hospital_id,
                Prescription.is_active == True
            )
        )

    # ========================================================
    # RETURN
    # ========================================================

    prescriptions = result.scalars().all()

    return prescriptions

# ============================================================
# GET PRESCRIPTION BY ID
#
# Super Admin      -> Any hospital
# Hospital Admin   -> Own hospital
# Doctor           -> Own prescriptions only
# Nurse            -> Own hospital
# Pharmacist       -> Own hospital
# Patient          -> Own prescriptions only
# ============================================================

@router.get(
    "/{prescription_id}",
    response_model=PrescriptionResponse
)
async def get_prescription(
    prescription_id: int,
    db: DBSessionDep,
    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # GET PRESCRIPTION
    # ========================================================

    prescription_result = await db.execute(
        select(Prescription).where(
            Prescription.id == prescription_id
        )
    )

    prescription = prescription_result.scalar_one_or_none()

    if prescription is None:
        raise HTTPException(
            status_code=404,
            detail="Prescription not found"
        )

    # ========================================================
    # CHECK ACTIVE
    # ========================================================

    if not prescription.is_active:

        raise HTTPException(
            status_code=404,
            detail="Prescription not found"
        )

    # ========================================================
    # GET MEDICAL RECORD
    # ========================================================

    record_result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id
            == prescription.medical_record_id
        )
    )

    medical_record = record_result.scalar_one_or_none()

    if medical_record is None:
        raise HTTPException(
            status_code=404,
            detail="Medical Record not found"
        )

    # ========================================================
    # SUPER ADMIN
    # role_id = 1
    #
    # Can access any prescription
    # ========================================================

    if current_user.role_id == 1:

        return prescription

    # ========================================================
    # PATIENT
    # role_id = 8
    #
    # Own prescription only
    # ========================================================

    if current_user.role_id == 8:

        if medical_record.patient_id != current_user.id:

            raise HTTPException(
                status_code=403,
                detail="You can only access your own prescriptions"
            )

        return prescription

    # ========================================================
    # DOCTOR
    # role_id = 3
    #
    # Own prescriptions only
    # ========================================================

    if current_user.role_id == 3:

        doctor_result = await db.execute(
            select(Doctor).where(
                Doctor.user_id == current_user.id
            )
        )

        doctor = doctor_result.scalar_one_or_none()

        if doctor is None:

            raise HTTPException(
                status_code=404,
                detail="Doctor profile not found"
            )

        # Doctor ownership check

        if medical_record.doctor_id != doctor.id:

            raise HTTPException(
                status_code=403,
                detail="You can only access your own prescriptions"
            )

        return prescription

    # ========================================================
    # HOSPITAL ADMIN / NURSE / PHARMACIST
    #
    # role_id = 2 / 4 / 7
    #
    # Own hospital only
    # ========================================================

    if current_user.role_id in [2, 4, 7]:

        # Get Doctor

        doctor_result = await db.execute(
            select(Doctor).where(
                Doctor.id == medical_record.doctor_id
            )
        )

        doctor = doctor_result.scalar_one_or_none()

        if doctor is None:

            raise HTTPException(
                status_code=404,
                detail="Doctor not found"
            )

        # Get Doctor's User

        doctor_user_result = await db.execute(
            select(User).where(
                User.id == doctor.user_id
            )
        )

        doctor_user = doctor_user_result.scalar_one_or_none()

        if doctor_user is None:

            raise HTTPException(
                status_code=404,
                detail="Doctor user not found"
            )

        # Hospital restriction

        if doctor_user.hospital_id != current_user.hospital_id:

            raise HTTPException(
                status_code=403,
                detail="You can only access prescriptions from your hospital"
            )

        return prescription

    # ========================================================
    # OTHER ROLES
    # ========================================================

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to access this prescription"
    )
# ============================================================
# UPDATE PRESCRIPTION
#
# Doctor only
#
# Rules:
# 1. User must be a Doctor
# 2. Doctor must have a Doctor profile
# 3. Prescription must exist
# 4. Prescription must be active
# 5. Prescription's medical record must exist
# 6. Prescription must belong to logged-in Doctor
# ============================================================

@router.put(
    "/{prescription_id}",
    response_model=PrescriptionResponse
)
async def update_prescription(
    prescription_id: int,
    prescription: PrescriptionUpdate,
    db: DBSessionDep,
    current_user: User = Depends(
        require_doctor
    ),
):

    # ========================================================
    # GET LOGGED-IN DOCTOR PROFILE
    # ========================================================

    doctor_result = await db.execute(
        select(Doctor).where(
            Doctor.user_id == current_user.id
        )
    )

    doctor = doctor_result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    # ========================================================
    # GET PRESCRIPTION
    # ========================================================

    result = await db.execute(
        select(Prescription).where(
            Prescription.id == prescription_id
        )
    )

    db_prescription = result.scalar_one_or_none()

    if db_prescription is None:
        raise HTTPException(
            status_code=404,
            detail="Prescription not found"
        )

    # ========================================================
    # CHECK PRESCRIPTION ACTIVE
    # ========================================================

    if not db_prescription.is_active:

        raise HTTPException(
            status_code=400,
            detail="Cannot update an inactive prescription"
        )

    # ========================================================
    # GET MEDICAL RECORD
    # ========================================================

    record_result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id
            == db_prescription.medical_record_id
        )
    )

    medical_record = record_result.scalar_one_or_none()

    if medical_record is None:
        raise HTTPException(
            status_code=404,
            detail="Medical Record not found"
        )

    # ========================================================
    # CHECK DOCTOR OWNERSHIP
    # ========================================================

    if medical_record.doctor_id != doctor.id:

        raise HTTPException(
            status_code=403,
            detail="You can only update your own prescriptions"
        )

    # ========================================================
    # UPDATE PRESCRIPTION
    # ========================================================

    update_data = prescription.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():

        # Don't allow changing ownership
        # through update request

        if key == "medical_record_id":
            continue

        setattr(
            db_prescription,
            key,
            value
        )

    # ========================================================
    # SAVE
    # ========================================================

    await db.commit()

    await db.refresh(
        db_prescription
    )

    return db_prescription
# ============================================================
# SOFT DELETE PRESCRIPTION
#
# Doctor only
#
# Rules:
# 1. User must be a Doctor
# 2. Doctor must have a Doctor profile
# 3. Prescription must exist
# 4. Prescription must be active
# 5. Prescription must belong to logged-in Doctor
# 6. Do NOT physically delete from database
# ============================================================

@router.delete(
    "/{prescription_id}"
)
async def delete_prescription(
    prescription_id: int,
    db: DBSessionDep,
    current_user: User = Depends(
        require_doctor
    ),
):

    # ========================================================
    # GET LOGGED-IN DOCTOR
    # ========================================================

    doctor_result = await db.execute(
        select(Doctor).where(
            Doctor.user_id == current_user.id
        )
    )

    doctor = doctor_result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    # ========================================================
    # GET PRESCRIPTION
    # ========================================================

    result = await db.execute(
        select(Prescription).where(
            Prescription.id == prescription_id
        )
    )

    db_prescription = result.scalar_one_or_none()

    if db_prescription is None:
        raise HTTPException(
            status_code=404,
            detail="Prescription not found"
        )

    # ========================================================
    # CHECK ALREADY DELETED
    # ========================================================

    if not db_prescription.is_active:

        raise HTTPException(
            status_code=400,
            detail="Prescription is already deleted"
        )

    # ========================================================
    # GET MEDICAL RECORD
    # ========================================================

    record_result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id
            == db_prescription.medical_record_id
        )
    )

    medical_record = record_result.scalar_one_or_none()

    if medical_record is None:
        raise HTTPException(
            status_code=404,
            detail="Medical Record not found"
        )

    # ========================================================
    # DOCTOR OWNERSHIP CHECK
    # ========================================================

    if medical_record.doctor_id != doctor.id:

        raise HTTPException(
            status_code=403,
            detail="You can only delete your own prescriptions"
        )

    # ========================================================
    # SOFT DELETE
    # ========================================================

    db_prescription.is_active = False

    await db.commit()

    return {
        "message": "Prescription deleted successfully"
    }