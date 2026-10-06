from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import (
    get_current_user,
    require_doctor,
)
from app.core.database import DBSessionDep

from app.models.lab_test_request import LabTestRequest
from app.models.medical_record import MedicalRecord
from app.models.doctor import Doctor
from app.models.user import User

from app.schema.lab_test_request import (
    LabTestRequestCreate,
    LabTestRequestResponse,
    LabTestRequestStatusUpdate,
)
router = APIRouter(
    prefix="/api/lab-test-requests",
    tags=["Lab Test Requests"],
)


# ============================================================
# CREATE LAB TEST REQUEST
#
# Only Doctor can create
# Doctor can create request only for:
# - His own medical record
# - His own patient
#
# Flow:
# Doctor → Lab Test Request → Lab Technician
# ============================================================

@router.post(
    "/",
    response_model=LabTestRequestResponse
)
async def create_lab_test_request(
    request: LabTestRequestCreate,
    db: DBSessionDep,
    current_user: User = Depends(require_doctor),
):

    # ========================================================
    # GET DOCTOR PROFILE
    # ========================================================

    doctor_result = await db.execute(
        select(Doctor).where(
            Doctor.user_id == current_user.id,
            Doctor.is_active == True
        )
    )

    doctor = doctor_result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor profile not found"
        )

    # ========================================================
    # OWNERSHIP CHECK
    #
    # Request doctor_id must match logged-in doctor
    # ========================================================

    if request.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only create lab requests for yourself"
        )

    # ========================================================
    # GET MEDICAL RECORD
    # ========================================================

    medical_record_result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id == request.medical_record_id,
            MedicalRecord.is_active == True
        )
    )

    medical_record = medical_record_result.scalar_one_or_none()

    if medical_record is None:
        raise HTTPException(
            status_code=404,
            detail="Medical record not found"
        )

    # ========================================================
    # MEDICAL RECORD DOCTOR CHECK
    # ========================================================

    if medical_record.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only create lab requests for your own medical records"
        )

    # ========================================================
    # PATIENT CHECK
    # ========================================================

    if medical_record.patient_id != request.patient_id:
        raise HTTPException(
            status_code=400,
            detail="Patient does not match the medical record"
        )

    # ========================================================
    # VERIFY PATIENT
    # ========================================================

    patient_result = await db.execute(
        select(User).where(
            User.id == request.patient_id,
            User.role_id == 8,
            User.is_active == True
        )
    )

    patient = patient_result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # ========================================================
    # VALIDATE PRIORITY
    # ========================================================

    allowed_priorities = [
        "NORMAL",
        "URGENT",
        "EMERGENCY"
    ]

    if request.priority not in allowed_priorities:
        raise HTTPException(
            status_code=400,
            detail="Priority must be NORMAL, URGENT, or EMERGENCY"
        )

    # ========================================================
    # CREATE REQUEST
    # ========================================================

    db_request = LabTestRequest(
        medical_record_id=request.medical_record_id,
        patient_id=request.patient_id,
        doctor_id=doctor.id,
        test_name=request.test_name,
        clinical_reason=request.clinical_reason,
        priority=request.priority,
        status="REQUESTED",
        requested_date=request.requested_date,
        is_active=True
    )

    db.add(db_request)

    await db.commit()
    await db.refresh(db_request)

    return db_request
@router.get(
    "/",
    response_model=list[LabTestRequestResponse]
)
async def get_lab_test_requests(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id == 1:
        result = await db.execute(
            select(LabTestRequest).where(
                LabTestRequest.is_active == True
            )
        )

    elif current_user.role_id == 6:
        result = await db.execute(
            select(LabTestRequest)
            .join(
                Doctor,
                LabTestRequest.doctor_id == Doctor.id
            )
            .join(
                User,
                Doctor.user_id == User.id
            )
            .where(
                User.hospital_id == current_user.hospital_id,
                LabTestRequest.is_active == True
            )
        )

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
            select(LabTestRequest).where(
                LabTestRequest.doctor_id == doctor.id,
                LabTestRequest.is_active == True
            )
        )

    elif current_user.role_id == 8:
        result = await db.execute(
            select(LabTestRequest).where(
                LabTestRequest.patient_id == current_user.id,
                LabTestRequest.is_active == True
            )
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access lab test requests"
        )

    return result.scalars().all()
@router.patch("/{request_id}/status", response_model=LabTestRequestResponse)
async def update_lab_test_request_status(
    request_id: int,
    status_data: LabTestRequestStatusUpdate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Only Lab Technician can update status
    if current_user.role_id != 6:
        raise HTTPException(
            status_code=403,
            detail="Only Lab Technician can update lab test request status"
        )

    # Get request with doctor and hospital information
    result = await db.execute(
        select(LabTestRequest)
        .join(Doctor, LabTestRequest.doctor_id == Doctor.id)
        .join(User, Doctor.user_id == User.id)
        .where(
            LabTestRequest.id == request_id,
            LabTestRequest.is_active == True,
            User.hospital_id == current_user.hospital_id
        )
    )

    lab_request = result.scalar_one_or_none()

    if lab_request is None:
        raise HTTPException(
            status_code=404,
            detail="Lab test request not found"
        )

    # Allowed statuses
    allowed_statuses = [
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELLED"
    ]

    if status_data.status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Status must be IN_PROGRESS, COMPLETED, or CANCELLED"
        )

    # Validate status transition
    current_status = lab_request.status
    new_status = status_data.status

    if current_status == "REQUESTED":
        if new_status not in ["IN_PROGRESS", "CANCELLED"]:
            raise HTTPException(
                status_code=400,
                detail="REQUESTED can only change to IN_PROGRESS or CANCELLED"
            )

    elif current_status == "IN_PROGRESS":
        if new_status != "COMPLETED":
            raise HTTPException(
                status_code=400,
                detail="IN_PROGRESS can only change to COMPLETED"
            )

    else:
        raise HTTPException(
            status_code=400,
            detail="This lab test request can no longer be updated"
        )

    # Update status
    lab_request.status = new_status

    await db.commit()
    await db.refresh(lab_request)

    return lab_request