
from pydantic import BaseModel, ConfigDict, Field


class BookCopyCreate(BaseModel):
    barcode: str = Field(min_length=1, max_length=50)


class BookCopyResponse(BaseModel):
    id: int
    book_id: int
    barcode: str
    status: str

    model_config = ConfigDict(from_attributes=True)
