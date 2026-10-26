
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.book import Book
from app.models.book_copy import BookCopy
from app.models.member import Member
from app.models.borrowing import Borrowing


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_books = db.scalar(
        select(func.count(Book.id))
    ) or 0

    total_copies = db.scalar(
        select(func.count(BookCopy.id))
    ) or 0

    available_copies = db.scalar(
        select(func.count(BookCopy.id)).where(
            BookCopy.status == "available"
        )
    ) or 0

    borrowed_copies = db.scalar(
        select(func.count(BookCopy.id)).where(
            BookCopy.status == "borrowed"
        )
    ) or 0

    active_members = db.scalar(
        select(func.count(Member.id)).where(
            Member.is_active.is_(True)
        )
    ) or 0

    active_loans = db.scalar(
        select(func.count(Borrowing.id)).where(
            Borrowing.returned_at.is_(None)
        )
    ) or 0

    overdue_loans = db.scalar(
        select(func.count(Borrowing.id)).where(
            Borrowing.returned_at.is_(None),
            Borrowing.due_at < func.now(),
        )
    ) or 0

    return {
        "total_books": total_books,
        "total_copies": total_copies,
        "available_copies": available_copies,
        "borrowed_copies": borrowed_copies,
        "active_members": active_members,
        "active_loans": active_loans,
        "overdue_loans": overdue_loans,
    }
