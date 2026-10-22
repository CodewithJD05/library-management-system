
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Borrowing(Base):
    __tablename__ = "borrowings"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id"),
        nullable=False,
        index=True,
    )

    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id"),
        nullable=False,
        index=True,
    )

    borrowed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=15),
        nullable=False,
    )

    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
