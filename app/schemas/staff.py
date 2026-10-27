from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StaffUserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(max_length=255)
    password: str = Field(min_length=12, max_length=128)
    role: str = "librarian"

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 characters")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if (
            not value
            or "@" not in value
            or value.startswith("@")
            or value.endswith("@")
            or " " in value
        ):
            raise ValueError("A valid email address is required")
        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"admin", "librarian"}:
            raise ValueError("Role must be admin or librarian")
        return value


class StaffUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=12, max_length=128)
    role: str | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 characters")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip().lower()
        if (
            not value
            or "@" not in value
            or value.startswith("@")
            or value.endswith("@")
            or " " in value
        ):
            raise ValueError("A valid email address is required")
        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip().lower()
        if value not in {"admin", "librarian"}:
            raise ValueError("Role must be admin or librarian")
        return value


class StaffUserStatusUpdate(BaseModel):
    is_active: bool


class StaffUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
