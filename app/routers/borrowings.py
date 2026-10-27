
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.book_copy import BookCopy
from app.models.borrowing import Borrowing
from app.models.fine import Fine
from app.models.member import Member
from app.models.staff_user import StaffUser
from app.routers.auth import get_current_staff_user
from app.schemas.borrowing import (
    BorrowingCreate,
    BorrowingDueDateUpdate,
    BorrowingResponse,
)
from app.utils.fine_calculator import DAILY_FINE_RATE, calculate_fine


router = APIRouter(prefix="/borrowings", tags=["Borrowings"])


CurrentStaff = Annotated[
    StaffUser,
    Depends(get_current_staff_user),
]

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


# Issue a book to a member
@router.post(
    "/",
    response_model=BorrowingResponse,
    status_code=status.HTTP_201_CREATED,
)
def borrow_book(
    borrowing_data: BorrowingCreate,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    try:
        book_copy = db.scalar(
            select(BookCopy)
            .where(BookCopy.id == borrowing_data.book_copy_id)
            .with_for_update()
        )

        if book_copy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book copy not found",
            )

        member = db.get(Member, borrowing_data.member_id)

        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found",
            )

        if not member.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive members cannot borrow books",
            )

        active_borrowing = db.scalar(
            select(Borrowing.id)
            .where(
                Borrowing.book_copy_id == book_copy.id,
                Borrowing.returned_at.is_(None),
            )
            .limit(1)
        )

        if (
            active_borrowing is not None
            or book_copy.status != "available"
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This book copy is already borrowed",
            )

        borrowing = Borrowing(
            book_copy_id=book_copy.id,
            member_id=member.id,
        )
        book_copy.status = "borrowed"
        db.add(borrowing)

        db.commit()
        db.refresh(borrowing)

        return borrowing

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This book copy is already borrowed",
        ) from None
    except Exception:
        db.rollback()
        raise


# Count overdue borrowings
@router.get("/overdue/count")
def count_overdue_borrowings(
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    now = datetime.now(timezone.utc)

    query = select(Borrowing.id).where(
        Borrowing.returned_at.is_(None),
        Borrowing.due_at < now,
    )

    overdue_count = len(db.scalars(query).all())

    return {"overdue_count": overdue_count}


# Extend a borrowing's due date
@router.patch(
    "/{borrowing_id}/due-date",
    response_model=BorrowingResponse,
)
def extend_due_date(
    borrowing_id: int,
    due_date_data: BorrowingDueDateUpdate,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    borrowing = db.get(Borrowing, borrowing_id)

    if borrowing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrowing record not found",
        )

    if borrowing.returned_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot extend the due date of a returned borrowing",
        )

    new_due_at = due_date_data.due_at

    if new_due_at.tzinfo is None or new_due_at.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The due date must include a timezone",
        )

    new_due_at = new_due_at.astimezone(timezone.utc)

    if new_due_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The new due date must be in the future",
        )

    # SQLite may return a datetime without timezone information.
    current_due_at = borrowing.due_at

    if current_due_at.tzinfo is None or current_due_at.utcoffset() is None:
        current_due_at = current_due_at.replace(tzinfo=timezone.utc)
    else:
        current_due_at = current_due_at.astimezone(timezone.utc)

    if new_due_at <= current_due_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The new due date must be later than the current due date",
        )

    borrowing.due_at = new_due_at

    try:
        db.commit()
        db.refresh(borrowing)
    except Exception:
        db.rollback()
        raise

    return borrowing


# List borrowing records with filters and pagination
@router.get("/", response_model=list[BorrowingResponse])
def list_borrowings(
    db: DatabaseSession,
    current_user: CurrentStaff,
    active_only: bool = False,
    overdue_only: bool = False,
    member_id: int | None = Query(default=None, ge=1),
    book_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
):
    query = select(Borrowing)

    if active_only:
        query = query.where(Borrowing.returned_at.is_(None))

    if overdue_only:
        now = datetime.now(timezone.utc)
        query = query.where(
            Borrowing.returned_at.is_(None),
            Borrowing.due_at < now,
        )

    if member_id is not None:
        query = query.where(Borrowing.member_id == member_id)

    if book_id is not None:
        query = query.join(
            BookCopy,
            Borrowing.book_copy_id == BookCopy.id,
        ).where(BookCopy.book_id == book_id)

    query = (
        query.order_by(Borrowing.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(query).all()


# Return a borrowed book and assess any applicable fine
@router.put(
    "/{borrowing_id}/return",
    response_model=BorrowingResponse,
)
def return_book(
    borrowing_id: int,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    try:
        borrowing = db.scalar(
            select(Borrowing)
            .where(Borrowing.id == borrowing_id)
            .with_for_update()
        )

        if borrowing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Borrowing record not found",
            )

        if borrowing.returned_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This book has already been returned",
            )

        # Lock the associated copy to protect its inventory state.
        book_copy = db.scalar(
            select(BookCopy)
            .where(BookCopy.id == borrowing.book_copy_id)
            .with_for_update()
        )

        if book_copy is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The associated book copy was not found",
            )

        return_time = datetime.now(timezone.utc)
        fine_amount = calculate_fine(borrowing.due_at, return_time)

        borrowing.returned_at = return_time
        book_copy.status = "available"

        if fine_amount > 0:
            existing_fine = db.scalar(
                select(Fine).where(
                    Fine.borrowing_id == borrowing.id
                )
            )

            if existing_fine is None:
                db.add(
                    Fine(
                        borrowing_id=borrowing.id,
                        amount=fine_amount,
                        daily_rate=DAILY_FINE_RATE,
                        status="unpaid",
                        assessed_at=return_time,
                    )
                )

        db.commit()
        db.refresh(borrowing)

        return borrowing

    except Exception:
        db.rollback()
        raise
