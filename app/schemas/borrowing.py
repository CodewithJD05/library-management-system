
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BorrowingCreate(BaseModel):
    book_id: int
    member_id: int


class BorrowingResponse(BaseModel):
    id: int
    book_id: int
    member_id: int
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
