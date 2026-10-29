
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.book import Book
from app.models.book_copy import BookCopy
from app.models.borrowing import Borrowing
from app.models.staff_user import StaffUser
from app.routers.auth import get_current_staff_user
from app.schemas.book_copy import BookCopyCreate, BookCopyResponse


router = APIRouter(prefix="/books", tags=["Book Copies"])


CurrentStaff = Annotated[
    StaffUser,
    Depends(get_current_staff_user),
]

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.post(
    "/{book_id}/copies",
    response_model=BookCopyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_book_copy(
    book_id: int,
    copy_data: BookCopyCreate,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    book = db.get(Book, book_id)

    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    book_copy = BookCopy(
        book_id=book_id,
        barcode=copy_data.barcode,
        status="available",
    )

    db.add(book_copy)

    try:
        db.commit()
        db.refresh(book_copy)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A book copy with this barcode already exists",
        ) from None

    return book_copy


@router.get(
    "/{book_id}/copies",
    response_model=list[BookCopyResponse],
)
def list_book_copies(
    book_id: int,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    book = db.get(Book, book_id)

    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    query = (
        select(BookCopy)
        .where(BookCopy.book_id == book_id)
        .order_by(BookCopy.id)
    )

    return db.scalars(query).all()


@router.delete(
    "/{book_id}/copies/{copy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_book_copy(
    book_id: int,
    copy_id: int,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    book_copy = db.scalar(
        select(BookCopy)
        .where(
            BookCopy.id == copy_id,
            BookCopy.book_id == book_id,
        )
        .with_for_update()
    )

    if book_copy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book copy not found",
        )

    has_borrowing_history = db.scalar(
        select(Borrowing.id)
        .where(Borrowing.book_copy_id == copy_id)
        .limit(1)
    )

    if has_borrowing_history is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This copy cannot be deleted because it has borrowing "
                "history. Keep the record to preserve library history."
            ),
        )

    try:
        db.delete(book_copy)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This copy cannot be deleted because it is referenced by other records.",
        ) from None

    return Response(status_code=status.HTTP_204_NO_CONTENT)
