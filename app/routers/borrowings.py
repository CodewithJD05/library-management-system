
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.book_copy import BookCopy
from app.models.member import Member
from app.models.borrowing import Borrowing
from app.schemas.borrowing import (
    BorrowingCreate,
    BorrowingResponse,
    BorrowingDueDateUpdate
)


router = APIRouter(prefix="/borrowings", tags=["Borrowings"])


@router.post(
    "/",
    response_model=BorrowingResponse,
    status_code=status.HTTP_201_CREATED,
)
def borrow_book(
    borrowing_data: BorrowingCreate,
    db: Session = Depends(get_db),
):
    book_copy = db.get(BookCopy, borrowing_data.book_copy_id)

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
        select(Borrowing.id).where(
            Borrowing.book_copy_id == book_copy.id,
            Borrowing.returned_at.is_(None),
        ).limit(1)
    )

    if active_borrowing is not None or book_copy.status != "available":
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

    try:
        db.commit()
        db.refresh(borrowing)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This book copy is already borrowed",
        )

    return borrowing





@router.get("/overdue/count")
def count_overdue_borrowings(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)

    query = select(Borrowing.id).where(
        Borrowing.returned_at.is_(None),
        Borrowing.due_at < now,
    )

    overdue_count = len(db.scalars(query).all())

    return {"overdue_count": overdue_count}





@router.patch("/{borrowing_id}/due-date", response_model=BorrowingResponse)
def extend_due_date(
    borrowing_id: int,
    due_date_data: BorrowingDueDateUpdate,
    db: Session = Depends(get_db),
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

    
    current_due_at = borrowing.due_at

    # SQLite may return a datetime without timezone information.
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




@router.get("/", response_model=list[BorrowingResponse])
def list_borrowings(
    active_only: bool = False,
    overdue_only: bool = False,
    member_id: int | None = Query(default=None, ge=1),
    book_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
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

    query = query.order_by(Borrowing.id.desc()).offset(skip).limit(limit)
    return db.scalars(query).all()


@router.put("/{borrowing_id}/return", response_model=BorrowingResponse)
def return_book(
    borrowing_id: int,
    db: Session = Depends(get_db),
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
            detail="This book has already been returned",
        )

    book_copy = db.get(BookCopy, borrowing.book_copy_id)
    borrowing.returned_at = datetime.now(timezone.utc)

    if book_copy is not None:
        book_copy.status = "available"

    try:
        db.commit()
        db.refresh(borrowing)
    except Exception:
        db.rollback()
        raise

    return borrowing
