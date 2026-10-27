
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class BookCreate(BaseModel):
    @field_validator("title", "isbn")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value
    title: str = Field(min_length=1, max_length=200)
    isbn: str = Field(min_length=1, max_length=20)
    description: str | None = None
    published_year: int | None = Field(default=None, ge=1)


class BookResponse(BaseModel):
    id: int
    title: str
    isbn: str
    description: str | None
    published_year: int | None

    model_config = ConfigDict(from_attributes=True)




class BookUpdate(BaseModel):
    @field_validator("title", "isbn")
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return value

        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value
    title: str | None = Field(default=None, min_length=1, max_length=200)
    isbn: str | None = Field(default=None, min_length=1, max_length=20)
    description: str | None = None
    published_year: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_required_fields(self):
        for field in ("title", "isbn"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self
