from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import (
    get_current_user,
    require_doctor,
)
from app.core.database import DBSessionDep

from app.models.billing import Billing
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.user import User

from app.schema.billing import (
    BillingCreate,
    BillingUpdate,
    BillingResponse,
)
router = APIRouter(
    prefix="/api/billings",
    tags=["Billings"],
)


# ============================================================
# CREATE BILLING
#
# Only Doctor can create billing
#
# Validations:
# 1. Doctor profile must exist
# 2. Appointment must exist
# 3. Appointment must belong to logged-in doctor
# 4. Appointment patient must match billing patient
# 5. Appointment must be active
# 6. total_amount calculated by backend
# ============================================================

@router.post(
    "/",
    response_model=BillingResponse
)
async def create_billing(
    billing: BillingCreate,
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
    # GET APPOINTMENT
    # ========================================================

    appointment_result = await db.execute(
        select(Appointment).where(
            Appointment.id == billing.appointment_id
        )
    )

    appointment = appointment_result.scalar_one_or_none()

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    # ========================================================
    # ACTIVE APPOINTMENT CHECK
    # ========================================================

    if not appointment.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot create billing for an inactive appointment"
        )

    # ========================================================
    # DOCTOR OWNERSHIP CHECK
    # ========================================================

    if appointment.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only create billing for your own appointments"
        )

    # ========================================================
    # PATIENT VALIDATION
    # ========================================================

    if appointment.patient_id != billing.patient_id:
        raise HTTPException(
            status_code=400,
            detail="Patient does not match the appointment"
        )

    # ========================================================
    # CALCULATE TOTAL AMOUNT
    # ========================================================

    total_amount = (
        billing.doctor_fee
        + billing.lab_fee
        + billing.medicine_fee
        + billing.other_charges
    )

    # ========================================================
    # CREATE BILLING
    # ========================================================

    new_billing = Billing(
        appointment_id=billing.appointment_id,
        patient_id=billing.patient_id,
        doctor_fee=billing.doctor_fee,
        lab_fee=billing.lab_fee,
        medicine_fee=billing.medicine_fee,
        other_charges=billing.other_charges,
        total_amount=total_amount,
        payment_status=billing.payment_status,
        payment_method=billing.payment_method,
        billing_date=billing.billing_date,
        is_active=True,
    )

    db.add(new_billing)

    await db.commit()
    await db.refresh(new_billing)

    return new_billing

# ============================================================
# GET ALL BILLINGS
#
# Super Admin      -> All active billings
# Hospital Admin   -> Own hospital billings
# Doctor           -> Own billings
# Nurse            -> Own hospital billings
# Pharmacist       -> Own hospital billings
# Patient          -> Cannot access all billings
# ============================================================

@router.get(
    "/",
    response_model=list[BillingResponse]
)
async def get_all_billings(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # SUPER ADMIN
    # role_id = 1
    # ========================================================

    if current_user.role_id == 1:

        result = await db.execute(
            select(Billing).where(
                Billing.is_active == True
            )
        )

    # ========================================================
    # DOCTOR
    # role_id = 3
    #
    # Doctor can see billings for his own appointments
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
            select(Billing)
            .join(
                Appointment,
                Billing.appointment_id == Appointment.id
            )
            .where(
                Appointment.doctor_id == doctor.id,
                Billing.is_active == True
            )
        )

    # ========================================================
    # PATIENT
    # role_id = 8
    # ========================================================

    elif current_user.role_id == 8:

        raise HTTPException(
            status_code=403,
            detail="Patients can only view their own billings"
        )

    # ========================================================
    # HOSPITAL ADMIN / NURSE / PHARMACIST
    # role_id = 2 / 4 / 7
    #
    # Billing -> Appointment -> Doctor -> User
    # ========================================================

    elif current_user.role_id in [2, 4, 7]:

        result = await db.execute(
            select(Billing)
            .join(
                Appointment,
                Billing.appointment_id == Appointment.id
            )
            .join(
                Doctor,
                Appointment.doctor_id == Doctor.id
            )
            .join(
                User,
                Doctor.user_id == User.id
            )
            .where(
                User.hospital_id == current_user.hospital_id,
                Billing.is_active == True
            )
        )

    # ========================================================
    # OTHER ROLES
    # ========================================================

    else:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access billings"
        )

    return result.scalars().all()
# ============================================================
# GET BILLING BY ID
#
# Super Admin      -> Any active billing
# Hospital Admin   -> Own hospital
# Doctor           -> Own appointments/billings
# Nurse            -> Own hospital
# Pharmacist       -> Own hospital
# Patient          -> Own billing only
# ============================================================

@router.get(
    "/{billing_id}",
    response_model=BillingResponse
)
async def get_billing(
    billing_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # GET BILLING
    # ========================================================

    result = await db.execute(
        select(Billing).where(
            Billing.id == billing_id
        )
    )

    billing = result.scalar_one_or_none()

    if billing is None:
        raise HTTPException(
            status_code=404,
            detail="Billing not found"
        )

    # ========================================================
    # ACTIVE CHECK
    # ========================================================

    if not billing.is_active:
        raise HTTPException(
            status_code=404,
            detail="Billing not found"
        )

    # ========================================================
    # SUPER ADMIN
    # ========================================================

    if current_user.role_id == 1:
        return billing

    # ========================================================
    # PATIENT
    # ========================================================

    if current_user.role_id == 8:

        if billing.patient_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own billing"
            )

        return billing

    # ========================================================
    # DOCTOR
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

        appointment_result = await db.execute(
            select(Appointment).where(
                Appointment.id == billing.appointment_id
            )
        )

        appointment = appointment_result.scalar_one_or_none()

        if appointment is None:
            raise HTTPException(
                status_code=404,
                detail="Appointment not found"
            )

        if appointment.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own billings"
            )

        return billing

    # ========================================================
    # HOSPITAL ADMIN / NURSE / PHARMACIST
    # ========================================================

    if current_user.role_id in [2, 4, 7]:

        result = await db.execute(
            select(Billing)
            .join(
                Appointment,
                Billing.appointment_id == Appointment.id
            )
            .join(
                Doctor,
                Appointment.doctor_id == Doctor.id
            )
            .join(
                User,
                Doctor.user_id == User.id
            )
            .where(
                Billing.id == billing_id,
                User.hospital_id == current_user.hospital_id
            )
        )

        hospital_billing = result.scalar_one_or_none()

        if hospital_billing is None:
            raise HTTPException(
                status_code=403,
                detail="You can only view billings from your own hospital"
            )

        return hospital_billing

    # ========================================================
    # OTHER ROLES
    # ========================================================

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to access billing"
    )

# ============================================================
# UPDATE BILLING
#
# Only Doctor can update billing
# Doctor can update ONLY his own billings
#
# Cannot change:
# - appointment_id
# - patient_id
# - total_amount directly
#
# total_amount is recalculated by backend
# ============================================================

@router.put(
    "/{billing_id}",
    response_model=BillingResponse
)
async def update_billing(
    billing_id: int,
    billing: BillingUpdate,
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
    # GET BILLING
    # ========================================================

    result = await db.execute(
        select(Billing).where(
            Billing.id == billing_id
        )
    )

    db_billing = result.scalar_one_or_none()

    if db_billing is None:
        raise HTTPException(
            status_code=404,
            detail="Billing not found"
        )

    # ========================================================
    # ACTIVE CHECK
    # ========================================================

    if not db_billing.is_active:
        raise HTTPException(
            status_code=404,
            detail="Billing not found"
        )

    # ========================================================
    # GET APPOINTMENT
    # ========================================================

    appointment_result = await db.execute(
        select(Appointment).where(
            Appointment.id == db_billing.appointment_id
        )
    )

    appointment = appointment_result.scalar_one_or_none()

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    # ========================================================
    # DOCTOR OWNERSHIP CHECK
    # ========================================================

    if appointment.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own billings"
        )

    # ========================================================
    # UPDATE ALLOWED FIELDS
    # ========================================================

    update_data = billing.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(db_billing, key, value)

    # ========================================================
    # RECALCULATE TOTAL
    # ========================================================

    db_billing.total_amount = (
        db_billing.doctor_fee
        + db_billing.lab_fee
        + db_billing.medicine_fee
        + db_billing.other_charges
    )

    # ========================================================
    # SAVE
    # ========================================================

    await db.commit()
    await db.refresh(db_billing)

    return db_billing
# Soft Delete Billing
@router.delete("/{billing_id}")
async def delete_billing(
    billing_id: int,
    db: DBSessionDep,
):
    result = await db.execute(
        select(Billing).where(Billing.id == billing_id)
    )

    db_billing = result.scalar_one_or_none()

    if db_billing is None:
        raise HTTPException(
            status_code=404,
            detail="Billing not found"
        )

    db_billing.is_active = False

    await db.commit()

    return {
        "message": "Billing deleted successfully"
    }