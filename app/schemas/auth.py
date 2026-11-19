from datetime import datetime
from pydantic import BaseModel, ConfigDict

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    refresh_token: str | None = None

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str | None = None

class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None
