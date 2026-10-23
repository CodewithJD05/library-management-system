
from datetime import datetime, timezone

DAILY_FINE_RATE = 10


def calculate_fine(due_at: datetime, end_at: datetime) -> int:
    """Calculate the fine in rupees for complete overdue days."""
    if due_at.tzinfo is None or due_at.utcoffset() is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    else:
        due_at = due_at.astimezone(timezone.utc)

    if end_at.tzinfo is None or end_at.utcoffset() is None:
        end_at = end_at.replace(tzinfo=timezone.utc)
    else:
        end_at = end_at.astimezone(timezone.utc)

    overdue_seconds = (end_at - due_at).total_seconds()

    if overdue_seconds <= 0:
        return 0

    overdue_days = int(overdue_seconds // 86400)
    return overdue_days * DAILY_FINE_RATE
