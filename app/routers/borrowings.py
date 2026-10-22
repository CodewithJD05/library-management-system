
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import borrowing
from app.models.book import Book
from app.models.member import Member
from app.models.borrowing import Borrowing
from app.schemas.borrowing import BorrowingCreate, BorrowingResponse

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

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
    book = db.get(Book, borrowing_data.book_id)

    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
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
        select(Borrowing).where(
            Borrowing.book_id == borrowing_data.book_id,
            Borrowing.returned_at.is_(None),
        )
    )

    if active_borrowing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This book is already borrowed",
        )

    borrowing = Borrowing(**borrowing_data.model_dump())

    db.add(borrowing)

    try:
        db.commit()
        db.refresh(borrowing)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This book is already borrowed",
        )

    return borrowing






@router.get("/", response_model=list[BorrowingResponse])
def list_borrowings(
    active_only: bool = False,
    member_id: int | None = Query(default=None, ge=1),
    book_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(Borrowing)

    if active_only:
        query = query.where(Borrowing.returned_at.is_(None))

    if member_id is not None:
        query = query.where(Borrowing.member_id == member_id)

    if book_id is not None:
        query = query.where(Borrowing.book_id == book_id)

    query = (
        query
        .order_by(Borrowing.id.desc())
        .offset(skip)
        .limit(limit)
    )

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

    borrowing.returned_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(borrowing)
    except Exception:
        db.rollback()
        raise
    
    return borrowing