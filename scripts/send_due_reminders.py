"""Run daily by cron/task scheduler: python -m scripts.send_due_reminders."""
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.book import Book
from app.models.reservation import Reservation
from app.services.notifications import process_pending_notifications, queue_due_reminders
from app.services.reservations import allocate_book_availability


def main():
    with SessionLocal() as db:
        # Reassign expired reservation holds, even without an incoming API request.
        book_ids = db.scalars(select(Book.id).where(Book.id.in_(select(Reservation.book_id).where(Reservation.status == 'ready')))).all()
        for book_id in book_ids:
            db.scalar(select(Book).where(Book.id == book_id).with_for_update())
            allocate_book_availability(db, book_id)
            db.commit()
        queued = queue_due_reminders(db)
        sent = process_pending_notifications(db)
    print(f'Queued {queued} new due reminders; delivered {sent} emails')

if __name__ == '__main__':
    main()
