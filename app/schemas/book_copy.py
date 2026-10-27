
from pydantic import BaseModel, ConfigDict, Field, field_validator

class BookCopyCreate(BaseModel):
    @field_validator("barcode")
    @classmethod
    def validate_barcode(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Barcode cannot be empty")
        return value
    barcode: str = Field(min_length=1, max_length=50)


class BookCopyResponse(BaseModel):
    id: int
    book_id: int
    barcode: str
    status: str

    model_config = ConfigDict(from_attributes=True)
