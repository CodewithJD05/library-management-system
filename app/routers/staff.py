
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_db
from app.models.staff_user import StaffUser
from app.routers.auth import require_roles
from app.schemas.staff import (
    StaffUserCreate,
    StaffUserResponse,
    StaffUserStatusUpdate,
    StaffUserUpdate,
)


router = APIRouter(prefix="/staff", tags=["Staff Management"])

AdminUser = Annotated[
    StaffUser,
    Depends(require_roles("admin")),
]

DatabaseSession = Annotated[Session, Depends(get_db)]


def ensure_another_active_admin_exists(
    db: Session,
    staff_user: StaffUser,
) -> None:
    """Prevent removing the last active administrator."""
    if staff_user.role != "admin" or not staff_user.is_active:
        return

    active_admin_count = db.scalar(
        select(func.count())
        .select_from(StaffUser)
        .where(
            StaffUser.role == "admin",
            StaffUser.is_active.is_(True),
        )
    )

    if active_admin_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last active administrator",
        )


@router.post(
    "/",
    response_model=StaffUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_staff_user(
    staff_data: StaffUserCreate,
    db: DatabaseSession,
    current_user: AdminUser,
):
    existing_user = db.scalar(
        select(StaffUser).where(
            StaffUser.email == staff_data.email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A staff account with this email already exists",
        )

    new_staff_user = StaffUser(
        full_name=staff_data.full_name,
        email=staff_data.email,
        password_hash=hash_password(staff_data.password),
        role=staff_data.role,
        is_active=True,
    )

    db.add(new_staff_user)

    try:
        db.commit()
        db.refresh(new_staff_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create staff account; check for duplicate email",
        ) from None

    return new_staff_user


@router.get("/", response_model=list[StaffUserResponse])
def list_staff_users(
    db: DatabaseSession,
    current_user: AdminUser,
):
    return db.scalars(
        select(StaffUser).order_by(StaffUser.id)
    ).all()


@router.get("/{staff_id}", response_model=StaffUserResponse)
def get_staff_user(
    staff_id: int,
    db: DatabaseSession,
    current_user: AdminUser,
):
    staff_user = db.get(StaffUser, staff_id)

    if staff_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff account not found",
        )

    return staff_user


@router.patch("/{staff_id}", response_model=StaffUserResponse)
def update_staff_user(
    staff_id: int,
    staff_data: StaffUserUpdate,
    db: DatabaseSession,
    current_user: AdminUser,
):
    staff_user = db.get(StaffUser, staff_id)

    if staff_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff account not found",
        )

    changes = staff_data.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    # Prevent removing the last active administrator.
    if (
        changes.get("role") == "librarian"
        and staff_user.role == "admin"
        and staff_user.is_active
    ):
        ensure_another_active_admin_exists(db, staff_user)

    if "email" in changes:
        duplicate = db.scalar(
            select(StaffUser).where(
                StaffUser.email == changes["email"],
                StaffUser.id != staff_id,
            )
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A staff account with this email already exists",
            )

    if "password" in changes:
        changes["password_hash"] = hash_password(
            changes.pop("password")
        )

    for field, value in changes.items():
        setattr(staff_user, field, value)

    try:
        db.commit()
        db.refresh(staff_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not update staff account",
        ) from None

    return staff_user


@router.patch(
    "/{staff_id}/status",
    response_model=StaffUserResponse,
)
def update_staff_status(
    staff_id: int,
    status_data: StaffUserStatusUpdate,
    db: DatabaseSession,
    current_user: AdminUser,
):
    staff_user = db.get(StaffUser, staff_id)

    if staff_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff account not found",
        )

    if not status_data.is_active:
        ensure_another_active_admin_exists(db, staff_user)

        if staff_user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account",
            )

    staff_user.is_active = status_data.is_active

    try:
        db.commit()
        db.refresh(staff_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not update staff account status",
        ) from None

    return staff_user
