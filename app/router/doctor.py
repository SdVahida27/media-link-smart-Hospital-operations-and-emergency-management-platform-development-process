from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, func
from datetime import date
from app.core.database import DBSessionDep

from app.core.auth import (
    get_current_user,
    require_hospital_admin,
    require_doctor,
)
from app.models.doctor import Doctor
from app.models.user import User
from app.models.department import Department
from app.models.appointment import Appointment
from app.models.lab_report import LabReport
from app.models.medical_record import MedicalRecord
from app.models.prescription import Prescription

from app.schema.doctor import (
    DoctorCreate,
    DoctorUpdate,
    DoctorResponse,
)


router = APIRouter(
    prefix="/api/doctors",
    tags=["Doctors"]
)


# ============================================================
# CREATE DOCTOR
#
# Hospital Admin -> Own hospital only
# ============================================================

@router.post(
    "/",
    response_model=DoctorResponse
)
async def create_doctor(
    doctor: DoctorCreate,
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
            User.id == doctor.user_id
        )
    )

    db_user = result.scalar_one_or_none()

    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # ========================================================
    # USER MUST BE DOCTOR
    # ========================================================

    if db_user.role_id != 3:
        raise HTTPException(
            status_code=400,
            detail="Selected user is not a Doctor"
        )

    # ========================================================
    # DOCTOR MUST BELONG TO SAME HOSPITAL
    # ========================================================

    if db_user.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only create doctors for your hospital"
        )

    # ========================================================
    # GET DEPARTMENT
    # ========================================================

    result = await db.execute(
        select(Department).where(
            Department.id == doctor.department_id
        )
    )

    department = result.scalar_one_or_none()

    if department is None:
        raise HTTPException(
            status_code=404,
            detail="Department not found"
        )

    # ========================================================
    # DEPARTMENT MUST BELONG TO SAME HOSPITAL
    # ========================================================

    if department.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only assign doctors to departments from your hospital"
        )

    # ========================================================
    # CHECK DUPLICATE DOCTOR PROFILE
    # ========================================================

    result = await db.execute(
        select(Doctor).where(
            Doctor.user_id == doctor.user_id
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Doctor profile already exists"
        )

    # ========================================================
    # CREATE DOCTOR
    # ========================================================

    new_doctor = Doctor(
        user_id=doctor.user_id,
        department_id=doctor.department_id,
        specialization=doctor.specialization,
        qualification=doctor.qualification,
        experience=doctor.experience,
        consultation_fee=doctor.consultation_fee,
    )

    db.add(new_doctor)

    await db.commit()

    await db.refresh(new_doctor)

    return new_doctor
# ============================================================
# GET MY DOCTOR PROFILE
# Doctor only
#
# IMPORTANT:
# This route MUST come before /{doctor_id}
# ============================================================

@router.get("/my-profile")
async def get_my_doctor_profile(
    db: DBSessionDep,
    current_user: User = Depends(require_doctor),
):

    result = await db.execute(
        select(Doctor).where(
            Doctor.user_id == current_user.id
        )
    )

    doctor = result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "doctor_id": doctor.id,
        "hospital_id": current_user.hospital_id
    }
# ============================================================
# DOCTOR DASHBOARD
#
# Doctor -> Own dashboard only
# ============================================================

@router.get("/dashboard")
async def doctor_dashboard(
    db: DBSessionDep,
    current_user: User = Depends(require_doctor),
):

    # ========================================================
    # GET DOCTOR PROFILE
    # ========================================================

    result = await db.execute(
        select(Doctor).where(
            Doctor.user_id == current_user.id,
            Doctor.is_active == True
        )
    )

    doctor = result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    # ========================================================
    # TODAY'S DATE
    # ========================================================

    today = date.today()

    # ========================================================
    # TODAY'S APPOINTMENTS
    # ========================================================

    result = await db.execute(
        select(func.count(Appointment.id))
        .where(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == today,
            Appointment.is_active == True
        )
    )

    today_appointments = result.scalar() or 0

    # ========================================================
    # PENDING APPOINTMENTS
    # ========================================================

    result = await db.execute(
        select(func.count(Appointment.id))
        .where(
            Appointment.doctor_id == doctor.id,
            Appointment.status == "Pending",
            Appointment.is_active == True
        )
    )

    pending_appointments = result.scalar() or 0

    # ========================================================
    # COMPLETED APPOINTMENTS
    # ========================================================

    result = await db.execute(
        select(func.count(Appointment.id))
        .where(
            Appointment.doctor_id == doctor.id,
            Appointment.status == "Completed",
            Appointment.is_active == True
        )
    )

    completed_appointments = result.scalar() or 0

    # ========================================================
    # TOTAL UNIQUE PATIENTS
    # ========================================================

    result = await db.execute(
        select(
            func.count(
                func.distinct(Appointment.patient_id)
            )
        )
        .where(
            Appointment.doctor_id == doctor.id,
            Appointment.is_active == True
        )
    )

    total_patients = result.scalar() or 0

    # ========================================================
    # TOTAL LAB REPORTS
    # ========================================================

    result = await db.execute(
        select(func.count(LabReport.id))
        .where(
            LabReport.doctor_id == doctor.id,
            LabReport.is_active == True
        )
    )

    total_lab_reports = result.scalar() or 0

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "doctor_id": doctor.id,
        "user_id": current_user.id,
        "username": current_user.username,
        "hospital_id": current_user.hospital_id,
        "today": today,
        "today_appointments": today_appointments,
        "pending_appointments": pending_appointments,
        "completed_appointments": completed_appointments,
        "total_patients": total_patients,
        "total_lab_reports": total_lab_reports
    }
# ============================================================
# TODAY'S APPOINTMENTS
#
# Doctor -> Own appointments for today
# ============================================================

@router.get("/today-appointments")
async def get_today_appointments(
    db: DBSessionDep,
    current_user: User = Depends(require_doctor),
):

    # ========================================================
    # GET DOCTOR PROFILE
    # ========================================================

    result = await db.execute(
        select(Doctor).where(
            Doctor.user_id == current_user.id,
            Doctor.is_active == True
        )
    )

    doctor = result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    # ========================================================
    # TODAY
    # ========================================================

    today = date.today()

    # ========================================================
    # GET TODAY'S APPOINTMENTS
    # ========================================================

    result = await db.execute(
        select(Appointment)
        .where(
            Appointment.doctor_id == doctor.id,
            Appointment.appointment_date == today,
            Appointment.is_active == True
        )
        .order_by(
            Appointment.appointment_time
        )
    )

    appointments = result.scalars().all()

    # ========================================================
    # RESPONSE
    # ========================================================

    return [
        {
            "appointment_id": appointment.id,
            "patient_id": appointment.patient_id,
            "appointment_date": appointment.appointment_date,
            "appointment_time": appointment.appointment_time,
            "reason": appointment.reason,
            "status": appointment.status
        }
        for appointment in appointments
    ]
# ============================================================
# PATIENT HISTORY
#
# Doctor -> Own patients only
# ============================================================

@router.get("/patients/{patient_id}/history")
async def get_patient_history(
    patient_id: int,
    db: DBSessionDep,
    current_user: User = Depends(require_doctor),
):

    # ========================================================
    # GET DOCTOR PROFILE
    # ========================================================

    result = await db.execute(
        select(Doctor).where(
            Doctor.user_id == current_user.id,
            Doctor.is_active == True
        )
    )

    doctor = result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    # ========================================================
    # VERIFY PATIENT
    # ========================================================

    result = await db.execute(
        select(User).where(
            User.id == patient_id,
            User.role_id == 8
        )
    )

    patient = result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # ========================================================
    # GET APPOINTMENTS
    # ========================================================

    result = await db.execute(
        select(Appointment)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.doctor_id == doctor.id,
            Appointment.is_active == True
        )
        .order_by(
            Appointment.appointment_date.desc(),
            Appointment.appointment_time.desc()
        )
    )

    appointments = result.scalars().all()

    # ========================================================
    # GET MEDICAL RECORDS
    # ========================================================

    result = await db.execute(
        select(MedicalRecord)
        .where(
            MedicalRecord.patient_id == patient_id,
            MedicalRecord.doctor_id == doctor.id,
            MedicalRecord.is_active == True
        )
        .order_by(
            MedicalRecord.id.desc()
        )
    )

    medical_records = result.scalars().all()

    # ========================================================
    # GET PRESCRIPTIONS
    # ========================================================

    result = await db.execute(
        select(Prescription)
        .join(
            MedicalRecord,
            Prescription.medical_record_id
            == MedicalRecord.id
        )
        .where(
            MedicalRecord.patient_id == patient_id,
            MedicalRecord.doctor_id == doctor.id,
            Prescription.is_active == True
        )
        .order_by(
            Prescription.id.desc()
        )
    )

    prescriptions = result.scalars().all()

    # ========================================================
    # GET LAB REPORTS
    # ========================================================

    result = await db.execute(
        select(LabReport)
        .where(
            LabReport.patient_id == patient_id,
            LabReport.doctor_id == doctor.id,
            LabReport.is_active == True
        )
        .order_by(
            LabReport.report_date.desc()
        )
    )

    lab_reports = result.scalars().all()

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "patient": {
            "patient_id": patient.id,
            "username": patient.username,
            "hospital_id": patient.hospital_id
        },

        "appointments": [
            {
                "appointment_id": appointment.id,
                "appointment_date": appointment.appointment_date,
                "appointment_time": appointment.appointment_time,
                "reason": appointment.reason,
                "status": appointment.status
            }
            for appointment in appointments
        ],

        "medical_records": [
            {
                "medical_record_id": record.id,
                "appointment_id": record.appointment_id,
                "symptoms": record.symptoms,
                "diagnosis": record.diagnosis,
                "treatment": record.treatment,
                "notes": record.notes
            }
            for record in medical_records
        ],

        "prescriptions": [
            {
                "prescription_id": prescription.id,
                "medical_record_id": prescription.medical_record_id,
                "medicine_name": prescription.medicine_name,
                "dosage": prescription.dosage,
                "frequency": prescription.frequency,
                "duration": prescription.duration,
                "instructions": prescription.instructions
            }
            for prescription in prescriptions
        ],

        "lab_reports": [
            {
                "lab_report_id": report.id,
                "medical_record_id": report.medical_record_id,
                "test_name": report.test_name,
                "test_result": report.test_result,
                "remarks": report.remarks,
                "report_date": report.report_date
            }
            for report in lab_reports
        ]
    }

# ============================================================
# GET ALL DOCTORS
#
# Super Admin  -> All hospitals
# Hospital Admin -> Own hospital
# Doctor       -> Own hospital
# Nurse        -> Own hospital
# Patient      -> Own hospital
# ============================================================

@router.get(
    "/",
    response_model=list[DoctorResponse]
)
async def get_all_doctors(
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
            select(Doctor)
        )

    # ========================================================
    # OTHER USERS
    # Own hospital doctors only
    # ========================================================

    elif current_user.role_id in [2, 3, 4, 8]:

        result = await db.execute(
            select(Doctor)
            .join(
                User,
                Doctor.user_id == User.id
            )
            .where(
                User.hospital_id
                == current_user.hospital_id
            )
        )

    # ========================================================
    # OTHER ROLES
    # ========================================================

    else:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view doctors"
        )

    doctors = result.scalars().all()

    return doctors

    # ============================================================
# GET DOCTOR BY ID
#
# Super Admin      -> Any hospital
# Hospital Admin   -> Own hospital
# Doctor           -> Own hospital
# Nurse            -> Own hospital
# Patient          -> Own hospital
# ============================================================

@router.get(
    "/{doctor_id}",
    response_model=DoctorResponse
)
async def get_doctor(
    doctor_id: int,
    db: DBSessionDep,
    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # GET DOCTOR
    # ========================================================

    result = await db.execute(
        select(Doctor).where(
            Doctor.id == doctor_id
        )
    )

    doctor = result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # ========================================================
    # SUPER ADMIN
    # ========================================================

    if current_user.role_id == 1:
        return doctor

    # ========================================================
    # ALLOWED ROLES
    # ========================================================

    if current_user.role_id not in [2, 3, 4, 8]:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this doctor"
        )

    # ========================================================
    # GET DOCTOR'S USER
    # ========================================================

    user_result = await db.execute(
        select(User).where(
            User.id == doctor.user_id
        )
    )

    doctor_user = user_result.scalar_one_or_none()

    if doctor_user is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor user not found"
        )

    # ========================================================
    # HOSPITAL RESTRICTION
    # ========================================================

    if doctor_user.hospital_id != current_user.hospital_id:

        raise HTTPException(
            status_code=403,
            detail="You can only access doctors from your hospital"
        )

    return doctor

# ============================================================
# UPDATE DOCTOR
#
# Super Admin      -> Any doctor
# Hospital Admin   -> Own hospital doctor
# Doctor           -> Own profile only
# Nurse            -> Not allowed
# Patient          -> Not allowed
# ============================================================

@router.put(
    "/{doctor_id}",
    response_model=DoctorResponse
)
async def update_doctor(
    doctor_id: int,
    request: DoctorUpdate,
    db: DBSessionDep,
    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # GET DOCTOR
    # ========================================================

    result = await db.execute(
        select(Doctor).where(
            Doctor.id == doctor_id
        )
    )

    doctor = result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # ========================================================
    # GET DOCTOR USER
    # ========================================================

    user_result = await db.execute(
        select(User).where(
            User.id == doctor.user_id
        )
    )

    doctor_user = user_result.scalar_one_or_none()

    if doctor_user is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor user not found"
        )

    # ========================================================
    # SUPER ADMIN
    # Can update any doctor
    # ========================================================

    if current_user.role_id == 1:
        pass

    # ========================================================
    # HOSPITAL ADMIN
    # Own hospital doctors only
    # ========================================================

    elif current_user.role_id == 2:

        if doctor_user.hospital_id != current_user.hospital_id:

            raise HTTPException(
                status_code=403,
                detail="You can only update doctors from your hospital"
            )

    # ========================================================
    # DOCTOR
    # Own profile only
    # ========================================================

    elif current_user.role_id == 3:

        if doctor.user_id != current_user.id:

            raise HTTPException(
                status_code=403,
                detail="You can only update your own doctor profile"
            )

    # ========================================================
    # OTHER ROLES
    # ========================================================

    else:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to update doctor profiles"
        )

    # ========================================================
    # GET DEPARTMENT
    # ========================================================

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

    # ========================================================
    # DEPARTMENT HOSPITAL CHECK
    # ========================================================

    if current_user.role_id != 1:

        if department.hospital_id != current_user.hospital_id:

            raise HTTPException(
                status_code=403,
                detail="You can only assign departments from your hospital"
            )

    # ========================================================
    # UPDATE DOCTOR
    # ========================================================

    doctor.department_id = request.department_id
    doctor.specialization = request.specialization
    doctor.qualification = request.qualification
    doctor.experience = request.experience
    doctor.consultation_fee = request.consultation_fee
    doctor.is_active = request.is_active

    # ========================================================
    # SAVE
    # ========================================================

    await db.commit()

    await db.refresh(doctor)

    return doctor

# ============================================================
# DELETE DOCTOR
# Hospital Admin only
# ============================================================

@router.delete("/{doctor_id}")
async def delete_doctor(
    doctor_id: int,
    db: DBSessionDep,
    current_user: User = Depends(require_hospital_admin),
):

    result = await db.execute(
        select(Doctor).where(
            Doctor.id == doctor_id
        )
    )

    doctor = result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    await db.delete(doctor)
    await db.commit()

    return {
        "message": "Doctor deleted successfully"
    }