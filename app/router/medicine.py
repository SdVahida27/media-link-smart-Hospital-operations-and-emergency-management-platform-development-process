from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.database import DBSessionDep

from app.models.medicine import Medicine
from app.models.user import User

from app.schema.medicine import (
    MedicineCreate,
    MedicineUpdate,
    MedicineResponse,
)


router = APIRouter(
    prefix="/api/medicines",
    tags=["Medicines"],
)


# ---------------------------------------------------------
# CREATE MEDICINE
# Hospital Admin / Pharmacist
# ---------------------------------------------------------
@router.post(
    "/",
    response_model=MedicineResponse
)
async def create_medicine(
    medicine: MedicineCreate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id not in [2, 7]:
        raise HTTPException(
            status_code=403,
            detail="Only Hospital Admin or Pharmacist can create medicines"
        )

    if medicine.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only manage medicines for your own hospital"
        )

    if medicine.quantity < 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity cannot be negative"
        )

    if medicine.reorder_level < 0:
        raise HTTPException(
            status_code=400,
            detail="Reorder level cannot be negative"
        )

    new_medicine = Medicine(
        hospital_id=medicine.hospital_id,
        medicine_name=medicine.medicine_name,
        generic_name=medicine.generic_name,
        category=medicine.category,
        manufacturer=medicine.manufacturer,
        unit=medicine.unit,
        quantity=medicine.quantity,
        reorder_level=medicine.reorder_level,
        is_active=True,
    )

    db.add(new_medicine)
    await db.commit()
    await db.refresh(new_medicine)

    return new_medicine


# ---------------------------------------------------------
# GET ALL MEDICINES
# ---------------------------------------------------------
@router.get(
    "/",
    response_model=list[MedicineResponse]
)
async def get_medicines(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id == 1:
        result = await db.execute(
            select(Medicine).where(
                Medicine.is_active == True
            )
        )

    elif current_user.role_id in [2, 4, 7]:
        result = await db.execute(
            select(Medicine).where(
                Medicine.hospital_id == current_user.hospital_id,
                Medicine.is_active == True
            )
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to view medicine inventory"
        )

    return result.scalars().all()


# ---------------------------------------------------------
# GET AVAILABLE / LOW STOCK MEDICINES
# ---------------------------------------------------------
@router.get(
    "/low-stock",
    response_model=list[MedicineResponse]
)
async def get_low_stock_medicines(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id not in [1, 2, 7]:
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin, Hospital Admin or Pharmacist can view low stock medicines"
        )

    query = select(Medicine).where(
        Medicine.is_active == True,
        Medicine.quantity <= Medicine.reorder_level
    )

    if current_user.role_id != 1:
        query = query.where(
            Medicine.hospital_id == current_user.hospital_id
        )

    result = await db.execute(query)

    return result.scalars().all()


# ---------------------------------------------------------
# GET MEDICINE BY ID
# ---------------------------------------------------------
@router.get(
    "/{medicine_id}",
    response_model=MedicineResponse
)
async def get_medicine(
    medicine_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Medicine).where(
            Medicine.id == medicine_id,
            Medicine.is_active == True
        )
    )

    medicine = result.scalar_one_or_none()

    if medicine is None:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    if current_user.role_id == 1:
        return medicine

    if current_user.role_id not in [2, 4, 7]:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to view this medicine"
        )

    if medicine.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only view medicines from your own hospital"
        )

    return medicine


# ---------------------------------------------------------
# UPDATE MEDICINE
# ---------------------------------------------------------
@router.put(
    "/{medicine_id}",
    response_model=MedicineResponse
)
async def update_medicine(
    medicine_id: int,
    medicine_data: MedicineUpdate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id not in [2, 7]:
        raise HTTPException(
            status_code=403,
            detail="Only Hospital Admin or Pharmacist can update medicines"
        )

    result = await db.execute(
        select(Medicine).where(
            Medicine.id == medicine_id,
            Medicine.is_active == True
        )
    )

    medicine = result.scalar_one_or_none()

    if medicine is None:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    if medicine.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only update medicines from your own hospital"
        )

    update_data = medicine_data.model_dump(
        exclude_unset=True
    )

    if "quantity" in update_data and update_data["quantity"] < 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity cannot be negative"
        )

    if "reorder_level" in update_data and update_data["reorder_level"] < 0:
        raise HTTPException(
            status_code=400,
            detail="Reorder level cannot be negative"
        )

    for field, value in update_data.items():
        setattr(medicine, field, value)

    await db.commit()
    await db.refresh(medicine)

    return medicine


# ---------------------------------------------------------
# DELETE MEDICINE - SOFT DELETE
# ---------------------------------------------------------
@router.delete(
    "/{medicine_id}"
)
async def delete_medicine(
    medicine_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    if current_user.role_id not in [2, 7]:
        raise HTTPException(
            status_code=403,
            detail="Only Hospital Admin or Pharmacist can delete medicines"
        )

    result = await db.execute(
        select(Medicine).where(
            Medicine.id == medicine_id,
            Medicine.is_active == True
        )
    )

    medicine = result.scalar_one_or_none()

    if medicine is None:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    if medicine.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete medicines from your own hospital"
        )

    medicine.is_active = False

    await db.commit()

    return {
        "message": "Medicine deleted successfully"
    }