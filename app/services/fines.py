"""Fine response enrichment and billing inputs shared across API endpoints."""
from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.borrowing import Borrowing
from app.models.fine import Fine
from app.models.holiday import Holiday
from app.models.member import Member
from app.schemas.borrowing import BorrowingResponse
from app.utils.fine_calculator import fine_rate_for_category


def get_holiday_days(db: Session) -> set[date]:
    return set(db.scalars(select(Holiday.day)).all())


def borrowing_with_fine(db: Session, borrowing: Borrowing) -> BorrowingResponse:
    response = BorrowingResponse.model_validate(borrowing)
    member = db.get(Member, borrowing.member_id)
    response.daily_fine_rate = fine_rate_for_category(member.category if member else 'student')
    response.holiday_dates = get_holiday_days(db)
    if borrowing.returned_at is not None:
        fine = db.scalar(select(Fine.amount).where(Fine.borrowing_id == borrowing.id))
        if fine is not None:
            response.recorded_fine = fine
    return response
