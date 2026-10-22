
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class MemberCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)


class MemberResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MemberUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_required_fields(self):
        for field in ("full_name", "email", "is_active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self
