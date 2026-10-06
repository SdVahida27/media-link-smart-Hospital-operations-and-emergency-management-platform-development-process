from datetime import date
from app.models.doctor import Doctor
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.auth import get_current_user
from app.core.database import DBSessionDep

from app.models.appointment import Appointment
from app.models.queue import Queue
from app.models.user import User

from app.schema.queue import (
    QueueCreate,
    QueueUpdate,
    QueueResponse
)


router = APIRouter(
    prefix="/api/queues",
    tags=["Queues"]
)


# ============================================================
# CREATE QUEUE
# ============================================================

@router.post("/", response_model=QueueResponse)
async def create_queue(
    queue_data: QueueCreate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Only Receptionist
    if current_user.role_id != 5:
        raise HTTPException(
            status_code=403,
            detail="Only Receptionist can create queue"
        )

    # --------------------------------------------------------
    # Get active appointment
    # --------------------------------------------------------

    result = await db.execute(
        select(Appointment).where(
            Appointment.id == queue_data.appointment_id,
            Appointment.is_active == True
        )
    )

    appointment = result.scalar_one_or_none()

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Active appointment not found"
        )

    # --------------------------------------------------------
    # Check appointment already has queue
    # --------------------------------------------------------

    existing_result = await db.execute(
        select(Queue).where(
            Queue.appointment_id == queue_data.appointment_id
        )
    )

    existing_queue = existing_result.scalar_one_or_none()

    if existing_queue:
        raise HTTPException(
            status_code=400,
            detail="Queue already exists for this appointment"
        )

    # --------------------------------------------------------
    # Today's date
    # --------------------------------------------------------

    today = date.today()

    # --------------------------------------------------------
    # Get today's active queues for this doctor
    # --------------------------------------------------------

    token_result = await db.execute(
        select(Queue).where(
            Queue.queue_date == today,
            Queue.doctor_id == appointment.doctor_id,
            Queue.is_active == True
        )
    )

    existing_queues = token_result.scalars().all()

    # --------------------------------------------------------
    # Generate next token
    # --------------------------------------------------------

    if existing_queues:
        next_token = max(
            queue.token_number
            for queue in existing_queues
        ) + 1
    else:
        next_token = 1

    # --------------------------------------------------------
    # Create queue
    # --------------------------------------------------------

    queue = Queue(
        appointment_id=appointment.id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        token_number=next_token,
        queue_date=today,
        status="WAITING",
        is_active=True
    )

    db.add(queue)

    await db.commit()
    await db.refresh(queue)

    return queue
@router.get("/", response_model=list[QueueResponse])
async def get_all_queues(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    # Super Admin → all active queues
    if current_user.role_id == 1:
        result = await db.execute(
            select(Queue).where(
                Queue.is_active == True
            )
        )

    # Receptionist → queues from own hospital
    elif current_user.role_id == 5:
        result = await db.execute(
            select(Queue)
            .join(User, Queue.patient_id == User.id)
            .where(
                Queue.is_active == True,
                User.hospital_id == current_user.hospital_id
            )
        )

    # Doctor → only own queues
    elif current_user.role_id == 3:
        result = await db.execute(
            select(Queue).where(
                Queue.is_active == True,
                Queue.doctor_id == current_user.id
            )
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view queues"
        )

    return result.scalars().all()
# ============================================================
# GET QUEUE BY ID
# ============================================================

@router.get("/{queue_id}", response_model=QueueResponse)
async def get_queue_by_id(
    queue_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Get queue + patient hospital
    # --------------------------------------------------------

    result = await db.execute(
        select(
            Queue,
            User.hospital_id
        )
        .join(User, Queue.patient_id == User.id)
        .where(
            Queue.id == queue_id,
            Queue.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Active queue not found"
        )

    queue, patient_hospital_id = row

    # --------------------------------------------------------
    # Super Admin
    # --------------------------------------------------------

    if current_user.role_id == 1:
        return queue

    # --------------------------------------------------------
    # Receptionist → same hospital
    # --------------------------------------------------------

    if current_user.role_id == 5:

        if patient_hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this queue"
            )

        return queue

    # --------------------------------------------------------
    # Doctor → own queues
    # --------------------------------------------------------

    if current_user.role_id == 3:

        doctor_result = await db.execute(
            select(Queue)
            .join(Doctor, Queue.doctor_id == Doctor.id)
            .where(
                Queue.id == queue_id,
                Queue.is_active == True,
                Doctor.user_id == current_user.id
            )
        )

        doctor_queue = doctor_result.scalar_one_or_none()

        if doctor_queue is None:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this queue"
            )

        return doctor_queue

    # --------------------------------------------------------
    # Patient → own queue
    # --------------------------------------------------------

    if current_user.role_id == 8:

        if queue.patient_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to view this queue"
            )

        return queue

    # --------------------------------------------------------
    # Other roles
    # --------------------------------------------------------

    raise HTTPException(
        status_code=403,
        detail="You are not authorized to view queues"
    )
# ============================================================
# UPDATE QUEUE STATUS
# ============================================================

@router.patch("/{queue_id}", response_model=QueueResponse)
async def update_queue(
    queue_id: int,
    queue_data: QueueUpdate,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Get queue
    # --------------------------------------------------------

    result = await db.execute(
        select(
            Queue,
            User.hospital_id
        )
        .join(User, Queue.patient_id == User.id)
        .where(
            Queue.id == queue_id,
            Queue.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Active queue not found"
        )

    queue, patient_hospital_id = row

    # --------------------------------------------------------
    # Validate status
    # --------------------------------------------------------

    allowed_statuses = {
        "WAITING",
        "CALLED",
        "IN_CONSULTATION",
        "COMPLETED",
        "CANCELLED"
    }

    if queue_data.status is not None:

        if queue_data.status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid queue status"
            )

    # --------------------------------------------------------
    # Super Admin
    # --------------------------------------------------------

    if current_user.role_id == 1:
        pass

    # --------------------------------------------------------
    # Receptionist → same hospital
    # --------------------------------------------------------

    elif current_user.role_id == 5:

        if patient_hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to update this queue"
            )

    # --------------------------------------------------------
    # Doctor → own queue
    # --------------------------------------------------------

    elif current_user.role_id == 3:

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

        if queue.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to update this queue"
            )

    # --------------------------------------------------------
    # Other roles
    # --------------------------------------------------------

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to update queues"
        )

    # --------------------------------------------------------
    # Update fields
    # --------------------------------------------------------

    update_data = queue_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(queue, field, value)

    await db.commit()
    await db.refresh(queue)

    return queue
# ============================================================
# DELETE QUEUE - SOFT DELETE
# ============================================================

@router.delete("/{queue_id}")
async def delete_queue(
    queue_id: int,
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):

    # --------------------------------------------------------
    # Get active queue + patient hospital
    # --------------------------------------------------------

    result = await db.execute(
        select(
            Queue,
            User.hospital_id
        )
        .join(User, Queue.patient_id == User.id)
        .where(
            Queue.id == queue_id,
            Queue.is_active == True
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Active queue not found"
        )

    queue, patient_hospital_id = row

    # --------------------------------------------------------
    # Super Admin
    # --------------------------------------------------------

    if current_user.role_id == 1:
        pass

    # --------------------------------------------------------
    # Receptionist → same hospital
    # --------------------------------------------------------

    elif current_user.role_id == 5:

        if patient_hospital_id != current_user.hospital_id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to delete this queue"
            )

    # --------------------------------------------------------
    # Doctor → own queue
    # --------------------------------------------------------

    elif current_user.role_id == 3:

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

        if queue.doctor_id != doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to delete this queue"
            )

    # --------------------------------------------------------
    # Other roles
    # --------------------------------------------------------

    else:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to delete queues"
        )

    # --------------------------------------------------------
    # Soft delete
    # --------------------------------------------------------

    queue.is_active = False

    await db.commit()

    return {
        "message": "Queue deleted successfully"
    }