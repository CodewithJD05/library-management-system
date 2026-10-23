
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field,computed_field

from app.utils.fine_calculator import calculate_fine

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
        return calculate_fine(self.due_at, end_at)
