
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.borrowing import Borrowing
from app.models.member import Member
from app.models.staff_user import StaffUser
from app.routers.auth import get_current_staff_user
from app.schemas.borrowing import BorrowingResponse
from app.schemas.member import (
    MemberCreate,
    MemberResponse,
    MemberUpdate,
)


router = APIRouter(prefix="/members", tags=["Members"])

CurrentStaff = Annotated[
    StaffUser,
    Depends(get_current_staff_user),
]

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


class MemberStatusUpdate(BaseModel):
    is_active: bool


# Create a member
@router.post(
    "/",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_member(
    member_data: MemberCreate,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    existing_member = db.scalar(
        select(Member).where(Member.email == member_data.email)
    )

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A member with this email already exists",
        )

    member = Member(**member_data.model_dump())
    db.add(member)

    try:
        db.commit()
        db.refresh(member)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A member with this email already exists",
        ) from None

    return member


# List members with search and pagination
@router.get("/", response_model=list[MemberResponse])
def list_members(
    db: DatabaseSession,
    current_user: CurrentStaff,
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
):
    query = select(Member)

    if search:
        query = query.where(Member.full_name.ilike(f"%{search}%"))

    query = query.order_by(Member.id).offset(skip).limit(limit)

    return db.scalars(query).all()


# Get a member's borrowing history
@router.get(
    "/{member_id}/borrowings",
    response_model=list[BorrowingResponse],
)
def get_member_borrowing_history(
    member_id: int,
    db: DatabaseSession,
    current_user: CurrentStaff,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
):
    member = db.get(Member, member_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    query = (
        select(Borrowing)
        .where(Borrowing.member_id == member_id)
        .order_by(Borrowing.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(query).all()


# Get a member by ID
@router.get("/{member_id}", response_model=MemberResponse)
def get_member(
    member_id: int,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    member = db.get(Member, member_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    return member


# Update a member
@router.put("/{member_id}", response_model=MemberResponse)
def update_member(
    member_id: int,
    member_data: MemberUpdate,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    member = db.get(Member, member_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    update_data = member_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update",
        )

    for field, value in update_data.items():
        setattr(member, field, value)

    try:
        db.commit()
        db.refresh(member)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A member with this email already exists",
        ) from None

    return member


# Activate or deactivate a member
@router.patch("/{member_id}/status", response_model=MemberResponse)
def update_member_status(
    member_id: int,
    status_data: MemberStatusUpdate,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    member = db.get(Member, member_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    member.is_active = status_data.is_active

    db.commit()
    db.refresh(member)

    return member


# Delete a member
@router.delete(
    "/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_member(
    member_id: int,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    member = db.get(Member, member_id)

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )

    borrowing_exists = db.scalar(
        select(Borrowing.id)
        .where(Borrowing.member_id == member_id)
        .limit(1)
    )

    if borrowing_exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a member with borrowing history",
        )

    db.delete(member)
    db.commit()
