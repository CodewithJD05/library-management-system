
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
