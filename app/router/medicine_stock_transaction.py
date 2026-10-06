from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.database import DBSessionDep

from app.models.medicine import Medicine
from app.models.medicine_stock_transaction import MedicineStockTransaction
from app.models.user import User

from app.schema.medicine_stock_transaction import (
    MedicineStockTransactionCreate,
    MedicineStockTransactionResponse,
)


router = APIRouter(
    prefix="/api/medicine-stock",
    tags=["Medicine Stock"],
)


# ---------------------------------------------------------
# STOCK IN / STOCK OUT
# ---------------------------------------------------------
@router.post(
    "/transaction",
    response_model=MedicineStockTransactionResponse
)
async def create_stock_transaction(
    transaction: MedicineStockTransactionCreate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Only Hospital Admin or Pharmacist
    if current_user.role_id not in [2, 7]:
        raise HTTPException(
            status_code=403,
            detail="Only Hospital Admin or Pharmacist can manage medicine stock"
        )

    # Validate transaction type
    if transaction.transaction_type not in ["IN", "OUT"]:
        raise HTTPException(
            status_code=400,
            detail="Transaction type must be IN or OUT"
        )

    # Quantity must be positive
    if transaction.quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0"
        )

    # Validate date
    if transaction.transaction_date > date.today():
        raise HTTPException(
            status_code=400,
            detail="Transaction date cannot be in the future"
        )

    # Get medicine
    result = await db.execute(
        select(Medicine).where(
            Medicine.id == transaction.medicine_id,
            Medicine.is_active == True
        )
    )

    medicine = result.scalar_one_or_none()

    if medicine is None:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    # Hospital isolation
    if medicine.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only manage medicines from your own hospital"
        )

    # STOCK OUT validation
    if transaction.transaction_type == "OUT":

        if transaction.quantity > medicine.quantity:
            raise HTTPException(
                status_code=400,
                detail="Insufficient stock"
            )

        medicine.quantity -= transaction.quantity

    # STOCK IN
    elif transaction.transaction_type == "IN":

        medicine.quantity += transaction.quantity

    # Create transaction record
    new_transaction = MedicineStockTransaction(
        medicine_id=transaction.medicine_id,
        transaction_type=transaction.transaction_type,
        quantity=transaction.quantity,
        reason=transaction.reason,
        transaction_date=transaction.transaction_date,
        performed_by=current_user.id,
        is_active=True,
    )

    db.add(new_transaction)

    await db.commit()
    await db.refresh(new_transaction)

    return new_transaction


# ---------------------------------------------------------
# GET STOCK TRANSACTION HISTORY
# ---------------------------------------------------------
@router.get(
    "/{medicine_id}",
    response_model=list[MedicineStockTransactionResponse]
)
async def get_stock_transactions(
    medicine_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Only Hospital Admin or Pharmacist
    if current_user.role_id not in [2, 7]:
        raise HTTPException(
            status_code=403,
            detail="Only Hospital Admin or Pharmacist can view stock history"
        )

    # Validate medicine
    medicine_result = await db.execute(
        select(Medicine).where(
            Medicine.id == medicine_id,
            Medicine.is_active == True
        )
    )

    medicine = medicine_result.scalar_one_or_none()

    if medicine is None:
        raise HTTPException(
            status_code=404,
            detail="Medicine not found"
        )

    # Hospital isolation
    if medicine.hospital_id != current_user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="You can only view stock history from your own hospital"
        )

    # Get history
    result = await db.execute(
        select(MedicineStockTransaction)
        .where(
            MedicineStockTransaction.medicine_id == medicine_id,
            MedicineStockTransaction.is_active == True
        )
        .order_by(
            MedicineStockTransaction.id.desc()
        )
    )

    return result.scalars().all()