from fastapi import APIRouter
from sqlalchemy import select

from app.core.database import DBSessionDep
from app.models.role import Role
from app.schema.role import RoleCreate, RoleUpdate, RoleResponse

router = APIRouter(
    prefix="/api/roles",
    tags=["Roles"]
)


# Create Role
@router.post("/", response_model=RoleResponse)
async def create_role(
    role: RoleCreate,
    db: DBSessionDep
):
    new_role = Role(
        name=role.name,
        description=role.description,
    )

    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)

    return new_role


# Get All Roles
@router.get("/", response_model=list[RoleResponse])
async def get_all_roles(
    db: DBSessionDep
):
    result = await db.execute(select(Role))
    roles = result.scalars().all()
    return roles


# Get Role By ID
@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    db: DBSessionDep
):
    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )

    role = result.scalar_one_or_none()

    if role is None:
        return {"message": "Role not found"}

    return role


# Update Role
@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role: RoleUpdate,
    db: DBSessionDep
):
    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )

    db_role = result.scalar_one_or_none()

    if db_role is None:
        return {"message": "Role not found"}

    db_role.name = role.name
    db_role.description = role.description
    db_role.is_active = role.is_active

    await db.commit()
    await db.refresh(db_role)

    return db_role


# Delete Role
@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: DBSessionDep
):
    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )

    db_role = result.scalar_one_or_none()

    if db_role is None:
        return {"message": "Role not found"}

    await db.delete(db_role)
    await db.commit()

    return {"message": "Role deleted successfully"}