from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.database import DBSessionDep

from app.models.user import User
from app.models.medicine import Medicine
from app.models.prescription import Prescription
from app.models.medical_record import MedicalRecord
from app.models.medicine_dispensing import MedicineDispensing

from app.schema.medicine_dispensing import (
    MedicineDispensingCreate,
    MedicineDispensingResponse,
)


router = APIRouter(
    prefix="/api/medicine-dispensing",
    tags=["Medicine Dispensing"],
)


# ============================================================
# DISPENSE MEDICINE
# ============================================================

@router.post(
    "/",
    response_model=MedicineDispensingResponse
)
async def dispense_medicine(
    dispensing: MedicineDispensingCreate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # --------------------------------------------------------
    # 1. Only Hospital Admin / Pharmacist
    # --------------------------------------------------------

    if current_user.role_id not in [2, 7]:
        raise HTTPException(
            status_code=403,
            detail="Only Hospital Admin or Pharmacist can dispense medicine"
        )

    # --------------------------------------------------------
    # 2. Validate quantity
    # --------------------------------------------------------

    if dispensing.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0"
        )

    # --------------------------------------------------------
    # 3. Validate dispensing date
    # --------------------------------------------------------

    if dispensing.dispensed_date > date.today():
        raise HTTPException(
            status_code=400,
            detail="Dispensing date cannot be in the future"
        )

    # --------------------------------------------------------
    # 4. Get prescription
    # --------------------------------------------------------

    prescription_result = await db.execute(
        select(Prescription).where(
            Prescription.id == dispensing.prescription_id,
            Prescription.is_active == True
        )
    )

    prescription = prescription_result.scalar_one_or_none()

    if prescription is None:
        raise HTTPException(
            status_code=404,
            detail="Prescription not found"
        )

    # --------------------------------------------------------
    # 5. Get medical record
    # --------------------------------------------------------

    medical_record_result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id == prescription.medical_record_id,
            MedicalRecord.is_active == True
        )
    )

    medical_record = medical_record_result.scalar_one_or_none()

    if medical_record is None:
        raise HTTPException(
            status_code=404,
            detail="Medical record not found"
        )

    # --------------------------------------------------------
    # 6. Get patient from medical record
    # --------------------------------------------------------

    patient_result = await db.execute(
        select(User).where(
            User.id == medical_record.patient_id,
            User.is_active == True
        )
    )

    patient = patient_result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    if patient.role_id != 8:
        raise HTTPException(
            status_code=400,
            detail="Medical record does not belong to a patient"
        )

    # --------------------------------------------------------
    # 7. Hospital isolation for patient
    # --------------------------------------------------------

    if patient.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only dispense medicine to patients from your own hospital"
        )

    # --------------------------------------------------------
    # 8. Get medicine
    # --------------------------------------------------------

    medicine_result = await db.execute(
        select(Medicine).where(
            Medicine.id == dispensing.medicine_id,
            Medicine.is_active == True
        )
    )

    medicine = medicine_result.scalar_one_or_none()

    if medicine is None:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    # --------------------------------------------------------
    # 9. Medicine hospital isolation
    # --------------------------------------------------------

    if medicine.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only dispense medicines from your own hospital"
        )

    # --------------------------------------------------------
    # 10. Validate medicine matches prescription
    # --------------------------------------------------------

    if (
        prescription.medicine_name.strip().lower()
        != medicine.medicine_name.strip().lower()
    ):
        raise HTTPException(
            status_code=400,
            detail="Medicine does not match prescription"
        )

    # --------------------------------------------------------
    # 11. Check stock
    # --------------------------------------------------------

    if dispensing.quantity > medicine.quantity:
        raise HTTPException(
            status_code=400,
            detail="Insufficient medicine stock"
        )

    # --------------------------------------------------------
    # 12. Deduct stock
    # --------------------------------------------------------

    medicine.quantity -= dispensing.quantity

    # --------------------------------------------------------
    # 13. Create dispensing record
    # --------------------------------------------------------

    new_dispensing = MedicineDispensing(
        prescription_id=dispensing.prescription_id,
        patient_id=patient.id,
        medicine_id=dispensing.medicine_id,
        quantity=dispensing.quantity,
        dispensed_by=current_user.id,
        dispensed_date=dispensing.dispensed_date,
        status="DISPENSED",
        remarks=dispensing.remarks,
        is_active=True,
    )

    db.add(new_dispensing)

    # --------------------------------------------------------
    # 14. Commit stock + dispensing record together
    # --------------------------------------------------------

    await db.commit()

    await db.refresh(new_dispensing)

    return new_dispensing


# ============================================================
# GET DISPENSING HISTORY
# ============================================================

@router.get(
    "/",
    response_model=list[MedicineDispensingResponse]
)
async def get_dispensing_history(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # 1. Role validation
    # --------------------------------------------------------

    if current_user.role_id not in [1, 2, 7]:
        raise HTTPException(
            status_code=403,
            detail="Only Admin or Pharmacist can view dispensing history"
        )

    # --------------------------------------------------------
    # 2. Super Admin → all dispensing records
    # --------------------------------------------------------

    if current_user.role_id == 1:

        result = await db.execute(
            select(MedicineDispensing)
            .where(
                MedicineDispensing.is_active == True
            )
            .order_by(
                MedicineDispensing.id.desc()
            )
        )

        return result.scalars().all()

    # --------------------------------------------------------
    # 3. Hospital Admin / Pharmacist → own hospital
    # --------------------------------------------------------

    result = await db.execute(
        select(MedicineDispensing)
        .join(
            Medicine,
            Medicine.id == MedicineDispensing.medicine_id
        )
        .where(
            MedicineDispensing.is_active == True,
            Medicine.hospital_id == current_user.hospital_id
        )
        .order_by(
            MedicineDispensing.id.desc()
        )
    )

    return result.scalars().all()