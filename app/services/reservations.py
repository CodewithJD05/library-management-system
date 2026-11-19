"""First-in-first-out reservation holds, assigned to individual physical copies."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.book_copy import BookCopy
from app.models.member import Member
from app.models.reservation import Reservation
from app.services.notifications import queue_email


def now_utc():
    return datetime.now(timezone.utc)


def expire_ready_holds(db: Session, book_id: int, now: datetime | None = None) -> None:
    now = now or now_utc()
    expired = db.scalars(select(Reservation).where(
        Reservation.book_id == book_id, Reservation.status == 'ready',
        Reservation.expires_at <= now).with_for_update()).all()
    for reservation in expired:
        reservation.status = 'expired'
        reservation.book_copy_id = None


def allocate_waiting_reservation(db: Session, copy: BookCopy, now: datetime | None = None) -> Reservation | None:
    now = now or now_utc()
    if copy.status != 'available':
        return None
    current = db.scalar(select(Reservation.id).where(Reservation.book_copy_id == copy.id,
                                                       Reservation.status == 'ready'))
    if current is not None:
        return None
    next_up = db.scalar(select(Reservation).where(Reservation.book_id == copy.book_id,
                                                  Reservation.status == 'waiting')
                        .order_by(Reservation.created_at, Reservation.id).limit(1).with_for_update())
    if next_up is None:
        return None
    next_up.status = 'ready'
    next_up.book_copy_id = copy.id
    next_up.ready_at = now
    next_up.expires_at = now + timedelta(hours=settings.reservation_hold_hours)
    member = db.get(Member, next_up.member_id)
    if member is not None:
        queue_email(db, f'reservation-ready-{next_up.id}', member.email,
                    'Your reserved library book is available',
                    f'Hello {member.full_name},\n\nA copy of book #{next_up.book_id} is now reserved for you. Collect copy #{copy.id} before {next_up.expires_at.isoformat()}.\n')
    return next_up


def allocate_book_availability(db: Session, book_id: int) -> None:
    """Call with book's PostgreSQL row locked from the caller."""
    # SessionLocal uses autoflush=False, so pending status changes must be visible to SQL queries.
    db.flush()
    expire_ready_holds(db, book_id)
    db.flush()
    available = db.scalars(select(BookCopy).where(BookCopy.book_id == book_id,
                                                   BookCopy.status == 'available')
                           .order_by(BookCopy.id).with_for_update()).all()
    for copy in available:
        allocate_waiting_reservation(db, copy)
        db.flush()
