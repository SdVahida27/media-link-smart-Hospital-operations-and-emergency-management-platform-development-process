from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select

from app.core.auth import get_current_user
from app.core.database import DBSessionDep
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.user import User
from app.schema.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
)
router = APIRouter(
    prefix="/api/appointments",
    tags=["Appointments"],
)


# Create Appointment
@router.post("/", response_model=AppointmentResponse)
async def create_appointment(
    request: AppointmentCreate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Check Patient
    result = await db.execute(
        select(User).where(User.id == request.patient_id)
    )

    patient = result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    if patient.role_id != 8:
        raise HTTPException(
            status_code=400,
            detail="Selected user is not a patient"
        )

    # Check Doctor
    result = await db.execute(
        select(Doctor).where(
            Doctor.id == request.doctor_id
        )
    )

    doctor = result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # Past Date Validation
    if request.appointment_date < date.today():
        raise HTTPException(
            status_code=400,
            detail="Appointment date cannot be in the past"
        )

    # Duplicate Slot Check
    result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.doctor_id == request.doctor_id,
                Appointment.appointment_date == request.appointment_date,
                Appointment.appointment_time == request.appointment_time,
            )
        )
    )

    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Doctor is already booked for this time slot"
        )

    appointment = Appointment(
        patient_id=request.patient_id,
        doctor_id=request.doctor_id,
        appointment_date=request.appointment_date,
        appointment_time=request.appointment_time,
        reason=request.reason,
    )

    db.add(appointment)

    await db.commit()
    await db.refresh(appointment)

    return appointment
# ============================================================
# GET ALL APPOINTMENTS
#
# Super Admin  -> All hospitals
# Hospital Admin -> Own hospital
# Doctor       -> Own appointments
# Nurse        -> Own hospital
# Patient      -> Own appointments
# ============================================================

@router.get(
    "/",
    response_model=list[AppointmentResponse]
)
async def get_all_appointments(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # SUPER ADMIN
    # ========================================================

    if current_user.role_id == 1:

        result = await db.execute(
            select(Appointment)
        )

    # ========================================================
    # PATIENT
    # Own appointments only
    # ========================================================

    elif current_user.role_id == 8:

        result = await db.execute(
            select(Appointment).where(
                Appointment.patient_id == current_user.id
            )
        )

    # ========================================================
    # DOCTOR
    # Own appointments only
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
            select(Appointment).where(
                Appointment.doctor_id == doctor.id
            )
        )

    # ========================================================
    # HOSPITAL ADMIN / NURSE
    # Own hospital appointments
    # ========================================================

    elif current_user.role_id in [2, 4]:

        result = await db.execute(
            select(Appointment)
            .join(
                Doctor,
                Appointment.doctor_id == Doctor.id
            )
            .join(
                User,
                Doctor.user_id == User.id
            )
            .where(
                User.hospital_id == current_user.hospital_id
            )
        )

    # ========================================================
    # OTHER ROLES
    # ========================================================

    else:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view appointments"
        )

    appointments = result.scalars().all()

    return appointments
# ============================================================
# GET APPOINTMENT BY ID
#
# Super Admin      -> Any appointment
# Hospital Admin   -> Own hospital
# Doctor           -> Own appointments only
# Nurse            -> Own hospital
# Patient          -> Own appointments only
# ============================================================

@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse
)
async def get_appointment(
    appointment_id: int,
    db: DBSessionDep,
    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # GET APPOINTMENT
    # ========================================================

    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id
        )
    )

    appointment = result.scalar_one_or_none()

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    # ========================================================
    # SUPER ADMIN
    # role_id = 1
    #
    # Can access any appointment
    # ========================================================

    if current_user.role_id == 1:

        return appointment

    # ========================================================
    # PATIENT
    # role_id = 8
    #
    # Own appointments only
    # ========================================================

    if current_user.role_id == 8:

        if appointment.patient_id != current_user.id:

            raise HTTPException(
                status_code=403,
                detail="You can only access your own appointments"
            )

        return appointment

    # ========================================================
    # DOCTOR
    # role_id = 3
    #
    # Own appointments only
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

        if appointment.doctor_id != doctor.id:

            raise HTTPException(
                status_code=403,
                detail="You can only access your own appointments"
            )

        return appointment

    # ========================================================
    # HOSPITAL ADMIN / NURSE
    # role_id = 2 / 4
    #
    # Own hospital only
    # ========================================================

    if current_user.role_id in [2, 4]:

        # Get Doctor

        doctor_result = await db.execute(
            select(Doctor).where(
                Doctor.id == appointment.doctor_id
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
                detail="You can only access appointments from your hospital"
            )

        return appointment

    # ========================================================
    # OTHER ROLES
    # ========================================================

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to access this appointment"
    )
# ============================================================
# UPDATE APPOINTMENT
#
# Super Admin      -> Any appointment
# Hospital Admin   -> Own hospital
# Doctor           -> Own appointments
# Patient          -> Own appointment
# Nurse            -> Not allowed
#
# Patient restriction:
# Patient can update only:
#     status
#     is_active
#
# Patient cannot change:
#     appointment_date
#     appointment_time
#     reason
# ============================================================

@router.put(
    "/{appointment_id}",
    response_model=AppointmentResponse
)
async def update_appointment(
    appointment_id: int,
    request: AppointmentUpdate,
    db: DBSessionDep,
    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # GET APPOINTMENT
    # ========================================================

    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id
        )
    )

    appointment = result.scalar_one_or_none()

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    # ========================================================
    # SUPER ADMIN
    # ========================================================

    if current_user.role_id == 1:

        appointment.appointment_date = (
            request.appointment_date
        )

        appointment.appointment_time = (
            request.appointment_time
        )

        appointment.reason = request.reason
        appointment.status = request.status
        appointment.is_active = request.is_active

    # ========================================================
    # HOSPITAL ADMIN
    # ========================================================

    elif current_user.role_id == 2:

        doctor_result = await db.execute(
            select(Doctor).where(
                Doctor.id == appointment.doctor_id
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

        if doctor_user is None:
            raise HTTPException(
                status_code=404,
                detail="Doctor user not found"
            )

        if doctor_user.hospital_id != current_user.hospital_id:

            raise HTTPException(
                status_code=403,
                detail="You can only update appointments from your hospital"
            )

        appointment.appointment_date = (
            request.appointment_date
        )

        appointment.appointment_time = (
            request.appointment_time
        )

        appointment.reason = request.reason
        appointment.status = request.status
        appointment.is_active = request.is_active

    # ========================================================
    # DOCTOR
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

        if appointment.doctor_id != doctor.id:

            raise HTTPException(
                status_code=403,
                detail="You can only update your own appointments"
            )

        appointment.appointment_date = (
            request.appointment_date
        )

        appointment.appointment_time = (
            request.appointment_time
        )

        appointment.reason = request.reason
        appointment.status = request.status
        appointment.is_active = request.is_active

    # ========================================================
    # PATIENT
    #
    # Patient can update only own appointment
    # and only status / active state.
    # ========================================================

    elif current_user.role_id == 8:

        if appointment.patient_id != current_user.id:

            raise HTTPException(
                status_code=403,
                detail="You can only update your own appointments"
            )

        # Prevent patient from changing
        # date/time/reason.

        appointment.status = request.status
        appointment.is_active = request.is_active

    # ========================================================
    # NURSE / OTHER ROLES
    # ========================================================

    else:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to update appointments"
        )

    # ========================================================
    # SAVE
    # ========================================================

    await db.commit()

    await db.refresh(appointment)

    return appointment
# ============================================================
# CANCEL APPOINTMENT
# SOFT DELETE
#
# Super Admin      -> Any appointment
# Hospital Admin   -> Own hospital
# Doctor           -> Own appointments
# Patient          -> Own appointments
# Nurse            -> Not allowed
# ============================================================

@router.delete("/{appointment_id}")
async def cancel_appointment(
    appointment_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # GET APPOINTMENT
    # ========================================================

    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id
        )
    )

    appointment = result.scalar_one_or_none()

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    # ========================================================
    # ALREADY CANCELLED
    # ========================================================

    if not appointment.is_active:
        raise HTTPException(
            status_code=400,
            detail="Appointment is already cancelled"
        )

    # ========================================================
    # SUPER ADMIN
    # ========================================================

    if current_user.role_id == 1:

        pass

    # ========================================================
    # PATIENT
    # Own appointment only
    # ========================================================

    elif current_user.role_id == 8:

        if appointment.patient_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only cancel your own appointments"
            )

    # ========================================================
    # DOCTOR
    # Own appointments only
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

        if appointment.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You can only cancel your own appointments"
            )

    # ========================================================
    # HOSPITAL ADMIN
    # Own hospital only
    # ========================================================

    elif current_user.role_id == 2:

        doctor_result = await db.execute(
            select(Doctor).where(
                Doctor.id == appointment.doctor_id
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

        if doctor_user is None:
            raise HTTPException(
                status_code=404,
                detail="Doctor user not found"
            )

        if doctor_user.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can only cancel appointments from your hospital"
            )

    # ========================================================
    # NURSE / OTHER ROLES
    # ========================================================

    else:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to cancel appointments"
        )

    # ========================================================
    # SOFT DELETE
    # ========================================================

    appointment.is_active = False
    appointment.status = "Cancelled"

    await db.commit()

    return {
        "message": "Appointment cancelled successfully"
    }