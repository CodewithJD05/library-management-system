
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Fine(Base):
    __tablename__ = "fines"

    __table_args__ = (
        CheckConstraint(
            "amount >= 0",
            name="ck_fines_amount_nonnegative",
        ),
        CheckConstraint(
            "daily_rate > 0",
            name="ck_fines_daily_rate_positive",
        ),
        CheckConstraint(
            "status IN ('unpaid', 'paid')",
            name="ck_fines_status_valid",
        ),
        CheckConstraint(
            "(status = 'unpaid' AND paid_at IS NULL) OR "
            "(status = 'paid' AND paid_at IS NOT NULL)",
            name="ck_fines_payment_timestamp_consistent",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    borrowing_id: Mapped[int] = mapped_column(
        ForeignKey("borrowings.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    daily_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("10.00"),
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unpaid",
    )

    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
