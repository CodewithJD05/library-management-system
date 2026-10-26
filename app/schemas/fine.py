
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FineResponse(BaseModel):
    id: int
    borrowing_id: int
    amount: float
    daily_rate: float
    status: str
    assessed_at: datetime
    paid_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
