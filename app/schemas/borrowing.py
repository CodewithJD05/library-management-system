
from datetime import datetime, timezone, date
from decimal import Decimal

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

    daily_fine_rate: Decimal = Field(default=Decimal("10.00"), exclude=True)
    holiday_dates: set[date] = Field(default_factory=set, exclude=True)
    recorded_fine: Decimal | None = Field(default=None, exclude=True)

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def fine_amount(self) -> float:
        if self.recorded_fine is not None:
            return float(self.recorded_fine)
        end_at = self.returned_at or datetime.now(timezone.utc)
        return float(calculate_fine(self.due_at, end_at, self.daily_fine_rate, self.holiday_dates))
