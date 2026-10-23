
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.book import Book
from app.models.book_copy import BookCopy
from app.schemas.book_copy import BookCopyCreate, BookCopyResponse

router = APIRouter(prefix="/books", tags=["Book Copies"])


@router.post(
    "/{book_id}/copies",
    response_model=BookCopyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_book_copy(
    book_id: int,
    copy_data: BookCopyCreate,
    db: Session = Depends(get_db),
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
        )

    return book_copy


@router.get(
    "/{book_id}/copies",
    response_model=list[BookCopyResponse],
)
def list_book_copies(
    book_id: int,
    db: Session = Depends(get_db),
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
