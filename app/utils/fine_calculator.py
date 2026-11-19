"""Billing policy: completed 24-hour overdue periods, excluding configured holiday dates."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from app.core.config import settings

DAILY_FINE_RATE = 10  # legacy default for student members


def normalize_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def fine_rate_for_category(category: str) -> Decimal:
    return Decimal(settings.faculty_daily_fine if category == 'faculty' else settings.student_daily_fine)


def calculate_fine(due_at: datetime, end_at: datetime, daily_rate: int | Decimal = DAILY_FINE_RATE,
                   holidays: set[date] | None = None) -> int | Decimal:
    """Charge each *complete* 24h overdue block if its local end date isn't a holiday.

    Dates use LIBRARY_TIMEZONE (Asia/Kolkata by default). Weekends count unless
    explicitly added to the holidays table. Historical amounts stay fixed on Fine.
    """
    due_at, end_at = normalize_utc(due_at), normalize_utc(end_at)
    completed_days = max(0, int((end_at - due_at).total_seconds() // 86400))
    if not holidays:
        return completed_days * daily_rate
    tz = ZoneInfo(settings.library_timezone)
    chargeable = sum((due_at + timedelta(days=day)).astimezone(tz).date() not in holidays
                     for day in range(1, completed_days + 1))
    return chargeable * daily_rate
