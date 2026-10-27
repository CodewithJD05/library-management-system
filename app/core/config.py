from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Library Management System API"
    debug: bool = False
    secret_key: SecretStr
    database_url: str
    access_token_expire_minutes: int = Field(default=30, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
