from fastapi import APIRouter
from sqlalchemy import select

from app.core.database import DBSessionDep
from app.models.hospital import Hospital
from app.schema.hospital import HospitalCreate, HospitalUpdate

router = APIRouter(
    prefix="/api/hospitals",
    tags=["Hospitals"]
)


# Create Hospital
@router.post("/")
async def create_hospital(
    hospital: HospitalCreate,
    db: DBSessionDep
):
    new_hospital = Hospital(
        name=hospital.name,
        email=hospital.email,
        phone=hospital.phone,
        address=hospital.address,
        city=hospital.city,
        state=hospital.state,
        country=hospital.country,
        pincode=hospital.pincode,
        logo=hospital.logo,
    )

    db.add(new_hospital)
    await db.commit()
    await db.refresh(new_hospital)

    return new_hospital


# Get All Hospitals
@router.get("/")
async def get_all_hospitals(db: DBSessionDep):
    result = await db.execute(select(Hospital))
    hospitals = result.scalars().all()
    return hospitals


# Get Hospital By ID
@router.get("/{hospital_id}")
async def get_hospital(
    hospital_id: int,
    db: DBSessionDep
):
    result = await db.execute(
        select(Hospital).where(Hospital.id == hospital_id)
    )

    hospital = result.scalar_one_or_none()

    if hospital is None:
        return {"message": "Hospital not found"}

    return hospital


# Update Hospital
@router.put("/{hospital_id}")
async def update_hospital(
    hospital_id: int,
    hospital: HospitalUpdate,
    db: DBSessionDep
):
    result = await db.execute(
        select(Hospital).where(Hospital.id == hospital_id)
    )

    db_hospital = result.scalar_one_or_none()

    if db_hospital is None:
        return {"message": "Hospital not found"}

    db_hospital.name = hospital.name
    db_hospital.email = hospital.email
    db_hospital.phone = hospital.phone
    db_hospital.address = hospital.address
    db_hospital.city = hospital.city
    db_hospital.state = hospital.state
    db_hospital.country = hospital.country
    db_hospital.pincode = hospital.pincode
    db_hospital.logo = hospital.logo
    db_hospital.is_active = hospital.is_active

    await db.commit()
    await db.refresh(db_hospital)

    return db_hospital
@router.delete("/{hospital_id}")
async def delete_hospital(
    hospital_id: int,
    db: DBSessionDep
):
    result = await db.execute(
        select(Hospital).where(Hospital.id == hospital_id)
    )

    hospital = result.scalar_one_or_none()

    if hospital is None:
        return {"message": "Hospital not found"}

    await db.delete(hospital)
    await db.commit()

    return {"message": "Hospital deleted successfully"}