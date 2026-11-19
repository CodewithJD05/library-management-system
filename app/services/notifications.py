"""Durable notification outbox. Run scripts/send_due_reminders via an external scheduler."""
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.borrowing import Borrowing
from app.models.book_copy import BookCopy
from app.models.email_notification import EmailNotification
from app.models.member import Member

logger = logging.getLogger(__name__)


def queue_email(db: Session, key: str, recipient: str, subject: str, body: str) -> None:
    if not db.scalar(select(EmailNotification.id).where(EmailNotification.event_key == key)):
        db.add(EmailNotification(event_key=key, recipient=recipient, subject=subject, body=body))


def queue_due_reminders(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    from datetime import timedelta
    future = now + timedelta(days=settings.reminder_days_before)
    results = db.execute(
        select(Borrowing, Member).join(Member, Member.id == Borrowing.member_id)
        .where(Borrowing.returned_at.is_(None), Borrowing.due_at > now, Borrowing.due_at <= future)
    ).all()
    queued = 0
    for borrowing, member in results:
        due_time = borrowing.due_at
        key = f'due-reminder-{borrowing.id}-{due_time.isoformat()}'
        if db.scalar(select(EmailNotification.id).where(EmailNotification.event_key == key)):
            continue
        queue_email(db, key, member.email, 'Library book due soon',
                    f'Hello {member.full_name},\n\nYour borrowing #{borrowing.id} is due on {due_time.isoformat()}. Please return or renew it before the due date.\n')
        queued += 1
    db.commit()
    return queued


def email_enabled() -> bool:
    return bool(settings.smtp_host and settings.smtp_from_email)


def process_pending_notifications(db: Session, limit: int = 50) -> int:
    """Sends at least once. Schedule a *single* worker or use PostgreSQL row locks."""
    if not email_enabled():
        logger.warning('SMTP_HOST and SMTP_FROM_EMAIL must be configured to send queued emails')
        return 0
    pending = db.scalars(
        select(EmailNotification).where(EmailNotification.status.in_(['pending', 'failed']), EmailNotification.attempts < 5)
        .order_by(EmailNotification.id).limit(limit).with_for_update(skip_locked=True)
    ).all()
    sent = 0
    for item in pending:
        msg = EmailMessage()
        msg['From'] = settings.smtp_from_email
        msg['To'] = item.recipient
        msg['Subject'] = item.subject
        msg.set_content(item.body)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                if settings.smtp_use_tls:
                    server.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    server.login(settings.smtp_username, settings.smtp_password.get_secret_value())
                server.send_message(msg)
            item.status = 'sent'
            item.sent_at = datetime.now(timezone.utc)
            item.last_error = None
            sent += 1
        except Exception as exc:
            item.status = 'failed'
            item.last_error = str(exc)[:500]
            logger.exception('Failed to send email notification id=%s', item.id)
        item.attempts += 1
        db.commit()
    return sent


def deliver_queued_notifications() -> None:
    """BackgroundTasks entry point; each task obtains its own database session."""
    from app.db.session import SessionLocal
    with SessionLocal() as session:
        process_pending_notifications(session)
