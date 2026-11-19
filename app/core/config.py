
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Library Management System API"
    debug: bool = False
    secret_key: SecretStr
    database_url: str
    access_token_expire_minutes: int = Field(default=30, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0, le=90)
    reservation_hold_hours: int = Field(default=48, gt=0, le=168)
    student_daily_fine: int = Field(default=10, gt=0)
    faculty_daily_fine: int = Field(default=5, gt=0)
    library_timezone: str = "Asia/Kolkata"
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    reminder_days_before: int = Field(default=1, ge=0, le=30)

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5500",
            "http://localhost:5500",
        ]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        cleaned_origins = [origin.strip().rstrip("/") for origin in origins]

        if any(not origin for origin in cleaned_origins):
            raise ValueError("CORS_ORIGINS cannot contain empty origins")

        if "*" in cleaned_origins:
            raise ValueError(
                "Wildcard CORS origins are not allowed"
            )

        return list(dict.fromkeys(cleaned_origins))

    @model_validator(mode="after")
    def validate_settings(self):
        secret = self.secret_key.get_secret_value()

        if len(secret) < 32:
            raise ValueError(
                "SECRET_KEY must contain at least 32 characters"
            )

        if secret == "replace_with_a_random_secret":
            raise ValueError(
                "Replace the example SECRET_KEY with a secure random value"
            )

        return self


settings = Settings()
