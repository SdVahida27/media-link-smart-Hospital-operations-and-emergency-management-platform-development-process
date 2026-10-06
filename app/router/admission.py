from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.database import DBSessionDep

from app.models.admission import Admission
from app.models.bed import Bed
from app.models.room import Room
from app.models.user import User

from app.schema.admission import (
    AdmissionCreate,
    AdmissionResponse
)

router = APIRouter(
    prefix="/api/admissions",
    tags=["Admissions"]
)


# ============================================================
# CREATE ADMISSION
# ============================================================

@router.post("/", response_model=AdmissionResponse)
async def create_admission(
    admission_data: AdmissionCreate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Allowed roles
    # Super Admin / Hospital Admin / Receptionist
    # --------------------------------------------------------

    if current_user.role_id not in [1, 2, 5]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin, Hospital Admin or Receptionist can admit patients"
        )

    # --------------------------------------------------------
    # Check patient
    # --------------------------------------------------------

    patient_result = await db.execute(
        select(User).where(
            User.id == admission_data.patient_id,
            User.role_id == 8
        )
    )

    patient = patient_result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # --------------------------------------------------------
    # Patient must belong to a hospital
    # --------------------------------------------------------

    if patient.hospital_id is None:
        raise HTTPException(
            status_code=400,
            detail="Patient is not associated with a hospital"
        )

    # --------------------------------------------------------
    # Hospital Admin / Receptionist → own hospital
    # --------------------------------------------------------

    if current_user.role_id in [2, 5]:

        if current_user.hospital_id != patient.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="Patient does not belong to your hospital"
            )

    # --------------------------------------------------------
    # Get available bed + room
    # --------------------------------------------------------

    bed_result = await db.execute(
        select(Bed, Room.hospital_id)
        .join(Room, Bed.room_id == Room.id)
        .where(
            Bed.id == admission_data.bed_id,
            Bed.is_active == True,
            Bed.status == "AVAILABLE",
            Room.is_active == True
        )
    )

    row = bed_result.first()

    if row is None:
        raise HTTPException(
            status_code=400,
            detail="Bed is not available"
        )

    bed, bed_hospital_id = row

    # --------------------------------------------------------
    # Bed and patient must belong to same hospital
    # --------------------------------------------------------

    if patient.hospital_id != bed_hospital_id:
        raise HTTPException(
            status_code=400,
            detail="Patient and bed must belong to the same hospital"
        )

    # --------------------------------------------------------
    # Hospital Admin / Receptionist → own hospital
    # --------------------------------------------------------

    if current_user.role_id in [2, 5]:

        if current_user.hospital_id != bed_hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to allocate this bed"
            )

    # --------------------------------------------------------
    # Check existing active admission
    # --------------------------------------------------------

    existing_result = await db.execute(
        select(Admission).where(
            Admission.patient_id == admission_data.patient_id,
            Admission.is_active == True,
            Admission.status == "ADMITTED"
        )
    )

    existing_admission = existing_result.scalar_one_or_none()

    if existing_admission:
        raise HTTPException(
            status_code=400,
            detail="Patient already has an active admission"
        )

    # --------------------------------------------------------
    # Create admission
    # --------------------------------------------------------

    admission = Admission(
        patient_id=admission_data.patient_id,
        bed_id=admission_data.bed_id,
        admission_date=admission_data.admission_date,
        reason=admission_data.reason,
        status="ADMITTED",
        is_active=True
    )

    db.add(admission)

    # --------------------------------------------------------
    # Allocate bed
    # --------------------------------------------------------

    bed.status = "OCCUPIED"

    await db.commit()
    await db.refresh(admission)

    return admission
# ============================================================
# GET ALL ADMISSIONS
# ============================================================

@router.get("/", response_model=list[AdmissionResponse])
async def get_all_admissions(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Super Admin → all active admissions
    # --------------------------------------------------------

    if current_user.role_id == 1:

        result = await db.execute(
            select(Admission).where(
                Admission.is_active == True
            )
        )

    # --------------------------------------------------------
    # Hospital Admin / Receptionist
    # → own hospital
    # --------------------------------------------------------

    elif current_user.role_id in [2, 5]:

        if current_user.hospital_id is None:
            raise HTTPException(
                status_code=403,
                detail="User is not associated with a hospital"
            )

        result = await db.execute(
            select(Admission)
            .join(User, Admission.patient_id == User.id)
            .where(
                Admission.is_active == True,
                User.hospital_id == current_user.hospital_id
            )
        )

    # --------------------------------------------------------
    # Doctor / Nurse
    # → own hospital
    # --------------------------------------------------------

    elif current_user.role_id in [3, 4]:

        if current_user.hospital_id is None:
            raise HTTPException(
                status_code=403,
                detail="User is not associated with a hospital"
            )

        result = await db.execute(
            select(Admission)
            .join(User, Admission.patient_id == User.id)
            .where(
                Admission.is_active == True,
                User.hospital_id == current_user.hospital_id
            )
        )

    # --------------------------------------------------------
    # Patient → own admissions only
    # --------------------------------------------------------

    elif current_user.role_id == 8:

        result = await db.execute(
            select(Admission).where(
                Admission.patient_id == current_user.id,
                Admission.is_active == True
            )
        )

    else:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view admissions"
        )

    return result.scalars().all()
# ============================================================
# GET ADMISSION BY ID
# ============================================================

@router.get("/{admission_id}", response_model=AdmissionResponse)
async def get_admission_by_id(
    admission_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Get active admission + patient hospital
    # --------------------------------------------------------

    result = await db.execute(
        select(Admission, User.hospital_id)
        .join(User, Admission.patient_id == User.id)
        .where(
            Admission.id == admission_id,
            Admission.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Active admission not found"
        )

    admission, hospital_id = row

    # --------------------------------------------------------
    # Super Admin
    # --------------------------------------------------------

    if current_user.role_id == 1:
        return admission

    # --------------------------------------------------------
    # Patient → own admission only
    # --------------------------------------------------------

    if current_user.role_id == 8:

        if admission.patient_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this admission"
            )

        return admission

    # --------------------------------------------------------
    # Hospital Admin / Doctor / Nurse / Receptionist
    # --------------------------------------------------------

    if current_user.role_id in [2, 3, 4, 5]:

        if current_user.hospital_id != hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this admission"
            )

        return admission

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to view admissions"
    )
# ============================================================
# DISCHARGE PATIENT
# ============================================================

@router.patch("/{admission_id}/discharge", response_model=AdmissionResponse)
async def discharge_patient(
    admission_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Allowed roles
    # Super Admin / Hospital Admin / Nurse / Receptionist
    # --------------------------------------------------------

    if current_user.role_id not in [1, 2, 4, 5]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin, Hospital Admin, Nurse or Receptionist can discharge patients"
        )

    # --------------------------------------------------------
    # Get active admission + hospital
    # --------------------------------------------------------

    result = await db.execute(
        select(Admission, User.hospital_id)
        .join(User, Admission.patient_id == User.id)
        .where(
            Admission.id == admission_id,
            Admission.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Active admission not found"
        )

    admission, hospital_id = row

    # --------------------------------------------------------
    # Hospital scope
    # --------------------------------------------------------

    if current_user.role_id in [2, 4, 5]:

        if current_user.hospital_id != hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to discharge this patient"
            )

    # --------------------------------------------------------
    # Check admission status
    # --------------------------------------------------------

    if admission.status != "ADMITTED":
        raise HTTPException(
            status_code=400,
            detail="Patient is not currently admitted"
        )

    # --------------------------------------------------------
    # Get bed
    # --------------------------------------------------------

    bed_result = await db.execute(
        select(Bed).where(
            Bed.id == admission.bed_id,
            Bed.is_active == True
        )
    )

    bed = bed_result.scalar_one_or_none()

    if bed is None:
        raise HTTPException(
            status_code=404,
            detail="Active bed not found"
        )

    # --------------------------------------------------------
    # Discharge admission
    # --------------------------------------------------------

    from datetime import date

    admission.status = "DISCHARGED"
    admission.discharge_date = date.today()
    admission.is_active = False

    # --------------------------------------------------------
    # Make bed available
    # --------------------------------------------------------

    bed.status = "AVAILABLE"

    await db.commit()
    await db.refresh(admission)

    return admission