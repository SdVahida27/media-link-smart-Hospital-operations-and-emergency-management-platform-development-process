from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import (
    get_current_user,
    require_doctor,
)
from app.core.database import DBSessionDep

from app.models.lab_report import LabReport
from app.models.medical_record import MedicalRecord
from app.models.doctor import Doctor
from app.models.user import User
from app.models.lab_test_request import LabTestRequest

from app.schema.lab_report import (
    LabReportCreate,
    LabReportUpdate,
    LabReportResponse,
)

router = APIRouter(
    prefix="/api/lab-reports",
    tags=["Lab Reports"],
)


# ============================================================
# CREATE LAB REPORT
#
# Doctor only
#
# Rules:
# 1. User must be Doctor
# 2. Doctor profile must exist
# 3. Medical Record must exist
# 4. Medical Record must be active
# 5. Report doctor must be logged-in Doctor
# 6. Medical Record doctor must be logged-in Doctor
# 7. Report patient must match Medical Record patient
# 8. Lab Test Request must exist
# 9. Lab Test Request must be active
# 10. Lab Test Request must be COMPLETED
# 11. Lab Test Request doctor must match logged-in Doctor
# 12. Lab Test Request patient must match report patient
# 13. Lab Test Request medical record must match report medical record
# ============================================================

@router.post(
    "/",
    response_model=LabReportResponse
)
async def create_lab_report(
    report: LabReportCreate,
    db: DBSessionDep,
    current_user: User = Depends(require_doctor),
):

    # ========================================================
    # GET LOGGED-IN DOCTOR
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
    # CHECK DOCTOR OWNERSHIP
    # ========================================================

    if report.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only create lab reports for yourself"
        )

    # ========================================================
    # GET MEDICAL RECORD
    # ========================================================

    record_result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id == report.medical_record_id
        )
    )

    medical_record = record_result.scalar_one_or_none()

    if medical_record is None:
        raise HTTPException(
            status_code=404,
            detail="Medical Record not found"
        )

    # ========================================================
    # CHECK MEDICAL RECORD ACTIVE
    # ========================================================

    if not medical_record.is_active:
        raise HTTPException(
            status_code=400,
            detail="Cannot create lab report for an inactive medical record"
        )

    # ========================================================
    # CHECK MEDICAL RECORD DOCTOR
    # ========================================================

    if medical_record.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only create lab reports for your own medical records"
        )

    # ========================================================
    # CHECK PATIENT
    # ========================================================

    if medical_record.patient_id != report.patient_id:
        raise HTTPException(
            status_code=400,
            detail="Patient does not match the medical record"
        )

    # ========================================================
    # GET LAB TEST REQUEST
    # ========================================================

    request_result = await db.execute(
        select(LabTestRequest).where(
            LabTestRequest.id == report.lab_test_request_id,
            LabTestRequest.is_active == True
        )
    )

    lab_test_request = request_result.scalar_one_or_none()

    if lab_test_request is None:
        raise HTTPException(
            status_code=404,
            detail="Lab test request not found"
        )

    # ========================================================
    # CHECK REQUEST STATUS
    # ========================================================

    if lab_test_request.status != "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Lab test request must be COMPLETED before creating a lab report"
        )

    # ========================================================
    # CHECK REQUEST DOCTOR
    # ========================================================

    if lab_test_request.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only create reports for your own lab test requests"
        )

    # ========================================================
    # CHECK REQUEST PATIENT
    # ========================================================

    if lab_test_request.patient_id != report.patient_id:
        raise HTTPException(
            status_code=400,
            detail="Patient does not match the lab test request"
        )

    # ========================================================
    # CHECK REQUEST MEDICAL RECORD
    # ========================================================

    if lab_test_request.medical_record_id != report.medical_record_id:
        raise HTTPException(
            status_code=400,
            detail="Medical record does not match the lab test request"
        )

    # ========================================================
    # CREATE LAB REPORT
    # ========================================================

    new_report = LabReport(
        medical_record_id=report.medical_record_id,
        lab_test_request_id=report.lab_test_request_id,
        patient_id=report.patient_id,
        doctor_id=report.doctor_id,
        test_name=report.test_name,
        test_result=report.test_result,
        remarks=report.remarks,
        report_date=report.report_date,
        is_active=True,
    )

    db.add(new_report)

    # ========================================================
    # SAVE
    # ========================================================

    await db.commit()

    await db.refresh(new_report)

    return new_report
# ============================================================
# GET ALL LAB REPORTS
#
# Super Admin      -> All hospitals
# Hospital Admin   -> Own hospital
# Doctor           -> Own lab reports
# Nurse            -> Own hospital
# Pharmacist       -> Own hospital
# Patient          -> Cannot access all reports
# ============================================================

@router.get(
    "/",
    response_model=list[LabReportResponse]
)
async def get_all_lab_reports(
    db: DBSessionDep,
    current_user: User = Depends(
        get_current_user
    ),
):

    # ========================================================
    # SUPER ADMIN
    # role_id = 1
    # ========================================================

    if current_user.role_id == 1:

        result = await db.execute(
            select(LabReport).where(
                LabReport.is_active == True
            )
        )

    # ========================================================
    # DOCTOR
    # role_id = 3
    #
    # Doctor can see ONLY his own lab reports
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
            select(LabReport).where(
                LabReport.doctor_id == doctor.id,
                LabReport.is_active == True
            )
        )

    # ========================================================
    # PATIENT
    # role_id = 8
    #
    # Patient cannot see all lab reports
    # ========================================================

    elif current_user.role_id == 8:

        raise HTTPException(
            status_code=403,
            detail="Patients can only view their own lab reports"
        )

    # ========================================================
    # HOSPITAL ADMIN / NURSE / PHARMACIST
    #
    # role_id = 2 / 4 / 7
    #
    # Only their hospital
    # ========================================================

    elif current_user.role_id in [2, 4, 7]:

        result = await db.execute(
            select(LabReport)
            .join(
                Doctor,
                LabReport.doctor_id == Doctor.id
            )
            .join(
                User,
                Doctor.user_id == User.id
            )
            .where(
                User.hospital_id == current_user.hospital_id,
                LabReport.is_active == True
            )
        )

    # ========================================================
    # OTHER ROLES
    # ========================================================

    else:

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access lab reports"
        )

    # ========================================================
    # RETURN
    # ========================================================

    reports = result.scalars().all()

    return reports
# ============================================================
# GET LAB REPORT BY ID
#
# Super Admin      -> Any active report
# Doctor           -> Own reports
# Patient          -> Own reports
# Hospital Admin   -> Own hospital reports
# Nurse            -> Own hospital reports
# Pharmacist       -> Own hospital reports
# ============================================================

@router.get(
    "/{report_id}",
    response_model=LabReportResponse
)
async def get_lab_report(
    report_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # ========================================================
    # GET REPORT
    # ========================================================

    result = await db.execute(
        select(LabReport).where(
            LabReport.id == report_id
        )
    )

    report = result.scalar_one_or_none()

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Lab Report not found"
        )

    # ========================================================
    # INACTIVE REPORT
    # ========================================================

    if not report.is_active:
        raise HTTPException(
            status_code=404,
            detail="Lab Report not found"
        )

    # ========================================================
    # SUPER ADMIN
    # role_id = 1
    #
    # Can view any active lab report
    # ========================================================

    if current_user.role_id == 1:
        return report

    # ========================================================
    # PATIENT
    # role_id = 8
    #
    # Can view ONLY their own lab reports
    # ========================================================

    if current_user.role_id == 8:

        if report.patient_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own lab reports"
            )

        return report

    # ========================================================
    # DOCTOR
    # role_id = 3
    #
    # Can view ONLY their own lab reports
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

        if report.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own lab reports"
            )

        return report

    # ========================================================
    # HOSPITAL ADMIN / NURSE / PHARMACIST
    #
    # role_id = 2 / 4 / 7
    #
    # Can view reports from their own hospital only
    # ========================================================

    if current_user.role_id in [2, 4, 7]:

        doctor_result = await db.execute(
            select(Doctor).where(
                Doctor.id == report.doctor_id
            )
        )

        doctor = doctor_result.scalar_one_or_none()

        if doctor is None:
            raise HTTPException(
                status_code=404,
                detail="Doctor not found"
            )

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

        if doctor_user.hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You can only view lab reports from your own hospital"
            )

        return report

    # ========================================================
    # OTHER ROLES
    # ========================================================

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to access lab reports"
    )

# ============================================================
# UPDATE LAB REPORT
#
# Only Doctor can update
# Doctor can update ONLY his own lab reports
#
# medical_record_id -> cannot change
# patient_id        -> cannot change
# doctor_id         -> cannot change
# ============================================================

@router.put(
    "/{report_id}",
    response_model=LabReportResponse
)
async def update_lab_report(
    report_id: int,
    report: LabReportUpdate,
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
    # GET LAB REPORT
    # ========================================================

    result = await db.execute(
        select(LabReport).where(
            LabReport.id == report_id
        )
    )

    db_report = result.scalar_one_or_none()

    if db_report is None:
        raise HTTPException(
            status_code=404,
            detail="Lab Report not found"
        )

    # ========================================================
    # ACTIVE CHECK
    # ========================================================

    if not db_report.is_active:
        raise HTTPException(
            status_code=404,
            detail="Lab Report not found"
        )

    # ========================================================
    # OWNERSHIP CHECK
    # ========================================================

    if db_report.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only update your own lab reports"
        )

    # ========================================================
    # UPDATE ALLOWED FIELDS ONLY
    # ========================================================

    update_data = report.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(db_report, key, value)

    # ========================================================
    # SAVE
    # ========================================================

    await db.commit()
    await db.refresh(db_report)

    return db_report
# ============================================================
# SOFT DELETE LAB REPORT
#
# Only Doctor can delete
# Doctor can delete ONLY his own lab reports
#
# Actual database row is NOT deleted.
# is_active is changed to False.
# ============================================================

@router.delete("/{report_id}")
async def delete_lab_report(
    report_id: int,
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
    # GET LAB REPORT
    # ========================================================

    result = await db.execute(
        select(LabReport).where(
            LabReport.id == report_id
        )
    )

    db_report = result.scalar_one_or_none()

    if db_report is None:
        raise HTTPException(
            status_code=404,
            detail="Lab Report not found"
        )

    # ========================================================
    # ACTIVE CHECK
    # ========================================================

    if not db_report.is_active:
        raise HTTPException(
            status_code=404,
            detail="Lab Report not found"
        )

    # ========================================================
    # OWNERSHIP CHECK
    # ========================================================

    if db_report.doctor_id != doctor.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own lab reports"
        )

    # ========================================================
    # SOFT DELETE
    # ========================================================

    db_report.is_active = False

    await db.commit()

    return {
        "message": "Lab Report deleted successfully"
    }