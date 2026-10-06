from fastapi import FastAPI
from sqlalchemy import text

from app.core.database import DBSessionDep

from app.router.auth import router as auth_router
from app.router.hospital import router as hospital_router
from app.router.role import router as role_router
from app.router.user import router as user_router
from app.router.department import router as department_router
from app.router.doctor import router as doctor_router
from app.router.appointment import router as appointment_router
from app.router.medical_record import router as medical_record_router
from app.router.prescription import router as prescription_router
from app.router.lab_report import router as lab_report_router
from app.router.billing import router as billing_router
from app.router.nurse import router as nurse_router
from app.router.pharmacist import router as pharmacist_router
from app.router.patient import router as patient_router
from app.router.receptionist import router as receptionist_router
from app.router.queue import router as queue_router
from app.router.bed import router as bed_router
from app.router.room import router as room_router
from app.router import admission
from app.models.lab_test_request import LabTestRequest
from app.router.lab_test_request import router as lab_test_request_router
from app.router.medicine import router as medicine_router
from app.router.medicine_stock_transaction import (
    router as medicine_stock_transaction_router
)
from app.router.medicine_dispensing import (
    router as medicine_dispensing_router
)

app = FastAPI(
    title="MedLink API",
    version="1.0.0",
    docs_url="/docs",
)

# Register Routers
app.include_router(hospital_router)
app.include_router(role_router)
app.include_router(user_router)
app.include_router(auth_router)
app.include_router(department_router)
app.include_router(doctor_router)
app.include_router(appointment_router)
app.include_router(medical_record_router)
app.include_router(prescription_router)
app.include_router(lab_report_router)
app.include_router(billing_router)
app.include_router(nurse_router)
app.include_router(pharmacist_router)
app.include_router(patient_router)
app.include_router(receptionist_router)
app.include_router(queue_router)
app.include_router(bed_router)
app.include_router(room_router)
app.include_router(admission.router)
app.include_router(lab_test_request_router)
app.include_router(medicine_router)
app.include_router(
    medicine_stock_transaction_router
)
app.include_router(medicine_dispensing_router)

# Root API
@app.get("/")
def root():
    return {"message": "Welcome to MedLink API"}


# Database Test API
@app.get("/db-test")
async def db_test(db: DBSessionDep):
    await db.execute(text("SELECT 1"))
    return {"message": "Database Connected Successfully"}