
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.member import Member
from app.schemas.member import MemberCreate, MemberResponse, MemberUpdate

from app.models.borrowing import Borrowing

router = APIRouter(prefix="/members", tags=["Members"])


# Create a member
@router.post("/", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(
    member_data: MemberCreate,
    db: Session = Depends(get_db),
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
        )

    return member


# List members with search and pagination
@router.get("/", response_model=list[MemberResponse])
def list_members(
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(Member)

    if search:
        query = query.where(Member.full_name.ilike(f"%{search}%"))

    query = query.order_by(Member.id).offset(skip).limit(limit)

    return db.scalars(query).all()


# Get a member by ID
@router.get("/{member_id}", response_model=MemberResponse)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
        )

    return member


# Delete a member

@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
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

