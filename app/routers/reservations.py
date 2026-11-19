"""Staff can reserve for any active member when all copies are unavailable."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.book import Book
from app.models.book_copy import BookCopy
from app.models.borrowing import Borrowing
from app.models.member import Member
from app.models.reservation import Reservation
from app.models.staff_user import StaffUser
from app.routers.auth import get_current_staff_user
from app.schemas.reservation import ReservationCreate, ReservationResponse
from app.services.reservations import allocate_book_availability
from app.services.notifications import email_enabled, deliver_queued_notifications

router = APIRouter(prefix='/reservations', tags=['Reservations'])
DB = Annotated[Session, Depends(get_db)]
Staff = Annotated[StaffUser, Depends(get_current_staff_user)]

@router.post('/', response_model=ReservationResponse, status_code=201)
def reserve_book(data: ReservationCreate, db: DB, current_user: Staff, background_tasks: BackgroundTasks):
    try:
        book = db.scalar(select(Book).where(Book.id == data.book_id).with_for_update())
        if book is None:
            raise HTTPException(status_code=404, detail='Book not found')
        member = db.get(Member, data.member_id)
        if member is None:
            raise HTTPException(status_code=404, detail='Member not found')
        if not member.is_active:
            raise HTTPException(status_code=400, detail='Inactive members cannot reserve books')
        if db.scalar(select(Reservation.id).where(Reservation.book_id == book.id,
                      Reservation.member_id == member.id, Reservation.status.in_(['waiting','ready']))) is not None:
            raise HTTPException(status_code=409, detail='Member already has an active reservation for this book')
        if db.scalar(select(Borrowing.id).join(BookCopy, Borrowing.book_copy_id == BookCopy.id)
                     .where(BookCopy.book_id == book.id, Borrowing.member_id == member.id,
                            Borrowing.returned_at.is_(None))) is not None:
            raise HTTPException(status_code=409, detail='Member already has an active borrowing of this book')
        copies = db.scalars(select(BookCopy).where(BookCopy.book_id == book.id).with_for_update()).all()
        if not copies:
            raise HTTPException(status_code=409, detail='This title has no physical copies to reserve')
        # First make sure an expired hold cannot block this request.
        allocate_book_availability(db, book.id)
        ready_copies = set(db.scalars(select(Reservation.book_copy_id).where(Reservation.book_id == book.id,
                                        Reservation.status == 'ready')).all())
        if any(copy.status == 'available' and copy.id not in ready_copies for copy in copies):
            raise HTTPException(status_code=409, detail='A copy is available; borrow it instead of reserving')
        reservation = Reservation(book_id=book.id, member_id=member.id, status='waiting')
        db.add(reservation)
        db.commit(); db.refresh(reservation)
        if email_enabled():
            background_tasks.add_task(deliver_queued_notifications)
        return reservation
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Active reservation already exists') from None
    except Exception:
        db.rollback(); raise

@router.get('/', response_model=list[ReservationResponse])
def list_reservations(db: DB, current_user: Staff, member_id: int | None = Query(None, ge=1),
                      book_id: int | None = Query(None, ge=1), status: str | None = None,
                      skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    q = select(Reservation)
    if member_id is not None: q = q.where(Reservation.member_id == member_id)
    if book_id is not None: q = q.where(Reservation.book_id == book_id)
    if status is not None:
        if status not in {'waiting','ready','fulfilled','cancelled','expired'}:
            raise HTTPException(status_code=422, detail='Invalid reservation status')
        q = q.where(Reservation.status == status)
    return db.scalars(q.order_by(Reservation.created_at.desc(), Reservation.id.desc()).offset(skip).limit(limit)).all()

@router.post('/{reservation_id}/cancel', response_model=ReservationResponse)
def cancel_reservation(reservation_id: int, db: DB, current_user: Staff, background_tasks: BackgroundTasks):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail='Reservation not found')
    book = db.scalar(select(Book).where(Book.id == reservation.book_id).with_for_update())
    reservation = db.scalar(select(Reservation).where(Reservation.id == reservation_id).with_for_update())
    if reservation.status not in {'waiting','ready'}:
        raise HTTPException(status_code=409, detail='Reservation is not active')
    reservation.status = 'cancelled'
    reservation.book_copy_id = None
    allocate_book_availability(db, book.id)
    db.commit();db.refresh(reservation)
    if email_enabled():
        background_tasks.add_task(deliver_queued_notifications)
    return reservation
