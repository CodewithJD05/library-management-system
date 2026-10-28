
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.book import Book
from app.models.book_copy import BookCopy
from app.models.staff_user import StaffUser
from app.routers.auth import get_current_staff_user
from app.schemas.book import BookCreate, BookResponse, BookUpdate


router = APIRouter(
    prefix="/books",
    tags=["Books"],
)

CurrentStaff = Annotated[
    StaffUser,
    Depends(get_current_staff_user),
]

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]



def is_duplicate_isbn_error(error: IntegrityError) -> bool:
    """Identify a duplicate ISBN across PostgreSQL and SQLite."""
    original_error = error.orig

    # PostgreSQL: inspect the reported constraint name.
    diagnostic = getattr(original_error, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)

    if constraint_name == "books_isbn_key":
        return True

    # SQLite: inspect the specific unique-column error.
    error_message = str(original_error)

    if error_message == "UNIQUE constraint failed: books.isbn":
        return True

    return False

def duplicate_isbn_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="A book with this ISBN already exists",
    )


@router.post(
    "/",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_book(
    book_data: BookCreate,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    existing_book = db.scalar(
        select(Book).where(Book.isbn == book_data.isbn)
    )

    if existing_book:
        raise duplicate_isbn_exception()

    book = Book(**book_data.model_dump())
    db.add(book)

    try:
        db.commit()
        db.refresh(book)
    except IntegrityError as error:
        db.rollback()

        if is_duplicate_isbn_error(error):
            raise duplicate_isbn_exception() from None

        raise

    return book


@router.get("/", response_model=list[BookResponse])
def list_books(
    db: DatabaseSession,
    current_user: CurrentStaff,
    search: str | None = None,
    published_year: int | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
):
    statement = select(Book)

    if search and search.strip():
        term = search.strip()

        conditions = [
            Book.title.ilike(f"%{term}%"),
            Book.isbn.ilike(f"%{term}%"),
        ]

        statement = statement.where(or_(*conditions))

    if published_year is not None:
        statement = statement.where(
            Book.published_year == published_year
        )

    statement = (
        statement
        .order_by(Book.id)
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(statement).all()


@router.get("/{book_id}", response_model=BookResponse)
def get_book(
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

    return book


@router.put("/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: DatabaseSession,
    current_user: CurrentStaff,
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
    except IntegrityError as error:
        db.rollback()

        if is_duplicate_isbn_error(error):
            raise duplicate_isbn_exception() from None

        raise

    return book


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_book(
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

    copy_exists = db.scalar(
        select(BookCopy.id)
        .where(BookCopy.book_id == book_id)
        .limit(1)
    )

    if copy_exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a book while physical copies exist",
        )

    db.delete(book)
    db.commit()
