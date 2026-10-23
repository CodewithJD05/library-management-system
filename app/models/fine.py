
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone

from app.db.base import Base


class Fine(Base):
    __tablename__ = "fines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    borrowing_id: Mapped[int] = mapped_column(
        ForeignKey("borrowings.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    daily_rate: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=10,
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
