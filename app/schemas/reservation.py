from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ReservationCreate(BaseModel):
    book_id: int = Field(gt=0)
    member_id: int = Field(gt=0)

class ReservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    book_id: int
    member_id: int
    book_copy_id: int | None
    status: str
    created_at: datetime
    ready_at: datetime | None
    expires_at: datetime | None
    fulfilled_at: datetime | None
