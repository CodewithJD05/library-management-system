
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.book import Book
from app.schemas.book import BookCreate, BookResponse, BookUpdate

from sqlalchemy.exc import IntegrityError

from sqlalchemy import select
from app.models.borrowing import Borrowing

router = APIRouter(
    prefix="/books",
    tags=["Books"],
)


@router.post(
    "/",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_book(
    book_data: BookCreate,
    db: Session = Depends(get_db),
):
    existing_book = (
        db.query(Book)
        .filter(Book.isbn == book_data.isbn)
        .first()
    )

    if existing_book:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A book with this ISBN already exists",
        )

    book = Book(**book_data.model_dump())

    db.add(book)
    db.commit()
    db.refresh(book)

    return book


@router.get("/", response_model=list[BookResponse])
def list_books(
    search: str | None = None,
    published_year: int | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Book)

    if search:
        query = query.filter(Book.title.ilike(f"%{search}%"))

    if published_year is not None:
        query = query.filter(Book.published_year == published_year)

    books = (
        query.order_by(Book.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return books




@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)

    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    return book


@router.put("/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: Session = Depends(get_db),
):
    book = db.get(Book, book_id)

    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    update_data = book_data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one field to update",
        )

    for field, value in update_data.items():
        setattr(book, field, value)

    try:
        db.commit()
        db.refresh(book)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A book with this ISBN already exists",
    )

    return book



@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
):
    book = db.get(Book, book_id)

    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    borrowing_exists = db.scalar(
        select(Borrowing.id)
        .where(Borrowing.book_id == book_id)
        .limit(1)
    )

    if borrowing_exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a book with borrowing history",
        )

    db.delete(book)
    db.commit()
