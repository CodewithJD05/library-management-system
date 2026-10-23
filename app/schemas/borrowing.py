
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field,computed_field


class BorrowingCreate(BaseModel):
    book_copy_id: int
    member_id: int

class BorrowingDueDateUpdate(BaseModel):
    due_at: datetime = Field(
        description="The new due date and time for the borrowing"
    )

class BorrowingResponse(BaseModel):
    id: int
    book_copy_id: int
    member_id: int
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def fine_amount(self) -> int:
        end_at = self.returned_at or datetime.now(timezone.utc)
        due_at = self.due_at

        if due_at.tzinfo is None or due_at.utcoffset() is None:
            due_at = due_at.replace(tzinfo=timezone.utc)

        if end_at.tzinfo is None or end_at.utcoffset() is None:
            end_at = end_at.replace(tzinfo=timezone.utc)

        overdue_seconds = (end_at - due_at).total_seconds()

        if overdue_seconds <= 0:
            return 0

        overdue_days = int(overdue_seconds // 86400)
        return overdue_days * 10
