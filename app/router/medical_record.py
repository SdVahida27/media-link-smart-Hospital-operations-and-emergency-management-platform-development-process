from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import (
    get_current_user,
    require_doctor,
    require_medical_record_viewer,
    require_doctor_or_hospital_admin,
)
from app.core.database import DBSessionDep

from app.models.medical_record import MedicalRecord
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.user import User

from app.schema.medical_record import (
    MedicalRecordCreate,
    MedicalRecordUpdate,
    MedicalRecordResponse,
)

router = APIRouter(
    prefix="/api/medical-records",
    tags=["Medical Records"],
)

# ============================================================
# CREATE MEDICAL RECORD
# Doctor only
#
# Doctor can create a record only:
# 1. For himself
# 2. For his own appointment
# 3. For the patient in that appointment
# ============================================================

@router.post(
    "/",
    response_model=MedicalRecordResponse
)
async def create_medical_record(
    record: MedicalRecordCreate,
    db: DBSessionDep,
    current_user: User = Depends(require_doctor),
):

    # ========================================================
    # Get logged-in doctor's profile
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
    # Doctor can use only his own doctor_id
    # ========================================================

    if record.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only create medical records for yourself"
        )

    # ========================================================
    # Check appointment
    # ========================================================

    appointment_result = await db.execute(
        select(Appointment).where(
            Appointment.id == record.appointment_id
        )
    )

    appointment = appointment_result.scalar_one_or_none()

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    # ========================================================
    # Appointment must belong to logged-in doctor
    # ========================================================

    if appointment.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only create records for your own appointments"
        )

    # ========================================================
    # Patient must belong to appointment
    # ========================================================

    if appointment.patient_id != record.patient_id:
        raise HTTPException(
            status_code=400,
            detail="Patient does not belong to this appointment"
        )

    # ========================================================
    # Create Medical Record
    # ========================================================

    new_record = MedicalRecord(
        appointment_id=record.appointment_id,
        patient_id=record.patient_id,
        doctor_id=doctor.id,
        symptoms=record.symptoms,
        diagnosis=record.diagnosis,
        treatment=record.treatment,
        notes=record.notes,
    )

    db.add(new_record)

    await db.commit()
    await db.refresh(new_record)

    return new_record
# ============================================================
# GET MEDICAL RECORDS
#
# Super Admin      -> All hospitals
# Hospital Admin   -> Own hospital
# Doctor           -> Own records
# Nurse            -> Own hospital
#
# Only ACTIVE records are returned
# ============================================================

@router.get(
    "/",
    response_model=list[MedicalRecordResponse]
)
async def get_all_medical_records(
    db: DBSessionDep,
    current_user: User = Depends(
        require_medical_record_viewer
    ),
):

    # ========================================================
    # SUPER ADMIN
    # role_id = 1
    # Can see active records from all hospitals
    # ========================================================

    if current_user.role_id == 1:

        result = await db.execute(
            select(MedicalRecord).where(
                MedicalRecord.is_active == True
            )
        )

    # ========================================================
    # DOCTOR
    # role_id = 3
    # Can see ONLY his/her own active records
    # ========================================================

    elif current_user.role_id == 3:

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

        result = await db.execute(
            select(MedicalRecord).where(
                MedicalRecord.doctor_id == doctor.id,
                MedicalRecord.is_active == True
            )
        )

    # ========================================================
    # HOSPITAL ADMIN / NURSE
    # role_id = 2 / 4
    #
    # Only active records from their hospital
    # ========================================================

    else:

        result = await db.execute(
            select(MedicalRecord)
            .join(
                Doctor,
                MedicalRecord.doctor_id == Doctor.id
            )
            .join(
                User,
                Doctor.user_id == User.id
            )
            .where(
                User.hospital_id == current_user.hospital_id,
                MedicalRecord.is_active == True
            )
        )

    records = result.scalars().all()

    return records
# ============================================================
# GET MEDICAL RECORD BY ID
#
# Super Admin       -> Any hospital
# Hospital Admin    -> Own hospital
# Doctor            -> Own medical records only
# Nurse             -> Own hospital
# Patient           -> Own records only
# ============================================================

@router.get(
    "/{record_id}",
    response_model=MedicalRecordResponse
)
async def get_medical_record(
    record_id: int,
    db: DBSessionDep,
    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # Get Medical Record
    # ========================================================

    result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id == record_id
        )
    )

    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Medical Record not found"
        )

    # ========================================================
    # SUPER ADMIN
    # role_id = 1
    # Can access any hospital's record
    # ========================================================

    if current_user.role_id == 1:
        return record

    # ========================================================
    # PATIENT
    # role_id = 8
    # Can access ONLY own records
    # ========================================================

    if current_user.role_id == 8:

        if record.patient_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only access your own medical records"
            )

        return record

    # ========================================================
    # Get Doctor who created the medical record
    # ========================================================

    doctor_result = await db.execute(
        select(Doctor).where(
            Doctor.id == record.doctor_id
        )
    )

    doctor = doctor_result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # ========================================================
    # Get Doctor's User
    # ========================================================

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

    # ========================================================
    # DOCTOR
    # role_id = 3
    # Can access ONLY his/her own records
    # ========================================================

    if current_user.role_id == 3:

        # Get logged-in doctor's profile
        current_doctor_result = await db.execute(
            select(Doctor).where(
                Doctor.user_id == current_user.id
            )
        )

        current_doctor = current_doctor_result.scalar_one_or_none()

        if current_doctor is None:
            raise HTTPException(
                status_code=404,
                detail="Doctor profile not found"
            )

        # Record belongs to another doctor
        if record.doctor_id != current_doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You can only access your own medical records"
            )

        return record

    # ========================================================
    # HOSPITAL ADMIN / NURSE
    #
    # role_id = 2 / 4
    # Can access records from their hospital
    # ========================================================

    if current_user.role_id in [2, 4]:

        if doctor_user.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can only access records from your hospital"
            )

        return record

    # ========================================================
    # OTHER ROLES
    # ========================================================

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to access this medical record"
    )
# ============================================================
# UPDATE MEDICAL RECORD
# Doctor only
#
# Doctor can update ONLY his own medical record.
# appointment_id, patient_id, doctor_id cannot be changed.
# ============================================================

@router.put(
    "/{record_id}",
    response_model=MedicalRecordResponse
)
async def update_medical_record(
    record_id: int,
    record: MedicalRecordUpdate,
    db: DBSessionDep,
    current_user: User = Depends(require_doctor),
):

    # ========================================================
    # Get logged-in doctor's profile
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
    # Get Medical Record
    # ========================================================

    result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id == record_id
        )
    )

    db_record = result.scalar_one_or_none()

    if db_record is None:
        raise HTTPException(
            status_code=404,
            detail="Medical Record not found"
        )

    # ========================================================
    # Doctor ownership check
    # ========================================================

    if db_record.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own medical records"
        )

    # ========================================================
    # Update ONLY editable fields
    # ========================================================

    update_data = record.model_dump(
        exclude_unset=True
    )

    allowed_fields = {
        "symptoms",
        "diagnosis",
        "treatment",
        "notes",
        "is_active",
    }

    for key, value in update_data.items():

        if key in allowed_fields:
            setattr(
                db_record,
                key,
                value
            )

    # ========================================================
    # Save
    # ========================================================

    await db.commit()
    await db.refresh(db_record)

    return db_record
# ============================================================
# DELETE MEDICAL RECORD
# Doctor + Hospital Admin
#
# Hospital restriction also applied
# ============================================================

@router.delete(
    "/{record_id}"
)
async def delete_medical_record(
    record_id: int,
    db: DBSessionDep,
    current_user: User = Depends(
        require_doctor_or_hospital_admin
    ),
):
    result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id == record_id
        )
    )

    db_record = result.scalar_one_or_none()

    if db_record is None:
        raise HTTPException(
            status_code=404,
            detail="Medical Record not found"
        )

    # Hospital Admin → check hospital
    if current_user.role_id == 2:

        doctor_result = await db.execute(
            select(Doctor).where(
                Doctor.id == db_record.doctor_id
            )
        )

        doctor = doctor_result.scalar_one_or_none()

        if doctor is None:
            raise HTTPException(
                status_code=404,
                detail="Doctor not found"
            )

        doctor_user_result = await db.execute(
            select(User).where(
                User.id == doctor.user_id
            )
        )

        doctor_user = doctor_user_result.scalar_one_or_none()

        if doctor_user.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can only delete records from your hospital"
            )

    # Doctor → own records only
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

        if db_record.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own medical records"
            )

    db_record.is_active = False

    await db.commit()

    return {
        "message": "Medical Record deleted successfully"
    }