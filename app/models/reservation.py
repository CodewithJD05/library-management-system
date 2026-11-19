from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, String, text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Reservation(Base):
    __tablename__ = 'reservations'
    __table_args__ = (
        CheckConstraint("status IN ('waiting','ready','fulfilled','cancelled','expired')", name='ck_reservations_status'),
        Index('uq_reservations_one_pending_per_member_book', 'member_id', 'book_id', unique=True,
              postgresql_where=text("status IN ('waiting','ready')"), sqlite_where=text("status IN ('waiting','ready')")),
        Index('uq_reservations_one_ready_per_copy', 'book_copy_id', unique=True,
              postgresql_where=text("status = 'ready'"), sqlite_where=text("status = 'ready'")),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey('books.id'), nullable=False, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey('members.id'), nullable=False, index=True)
    book_copy_id: Mapped[int | None] = mapped_column(ForeignKey('book_copies.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='waiting')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
