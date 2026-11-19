"""Authentication with 30-minute access tokens and rotated, revocable refresh sessions."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM, create_access_token, verify_password
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.staff_user import StaffUser
from app.schemas.auth import AuthSessionResponse, RefreshRequest, LogoutRequest, TokenResponse
from app.schemas.staff import StaffUserResponse

router = APIRouter(prefix='/auth', tags=['Authentication'])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login')


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def revoke_user_sessions(db: Session, staff_id: int) -> None:
    db.execute(update(AuthSession).where(AuthSession.staff_user_id == staff_id, AuthSession.revoked_at.is_(None)).values(revoked_at=datetime.now(timezone.utc)))


def issue_tokens(db: Session, staff: StaffUser) -> TokenResponse:
    refresh = new_refresh_token()
    auth_session = AuthSession(
        id=str(uuid.uuid4()), staff_user_id=staff.id,
        refresh_token_hash=digest(refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(auth_session)
    db.commit()
    return TokenResponse(access_token=create_access_token(str(staff.id), staff.role, auth_session.id), refresh_token=refresh)


@router.post('/login', response_model=TokenResponse)
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    user = db.scalar(select(StaffUser).where(StaffUser.email == form_data.username.lower().strip()))
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail='Invalid email or password', headers={'WWW-Authenticate': 'Bearer'})
    if not user.is_active:
        raise HTTPException(status_code=403, detail='Staff account is inactive')
    return issue_tokens(db, user)


@router.post('/refresh', response_model=TokenResponse)
def refresh_token(data: RefreshRequest, db: Annotated[Session, Depends(get_db)]):
    # The unique hash identifies a session. Row locking makes refresh rotation atomic on PostgreSQL.
    session = db.scalar(select(AuthSession).where(AuthSession.refresh_token_hash == digest(data.refresh_token)).with_for_update())
    now = datetime.now(timezone.utc)
    if session is None or session.revoked_at is not None or utc(session.expires_at) <= now:
        raise HTTPException(status_code=401, detail='Refresh token invalid or expired')
    user = db.get(StaffUser, session.staff_user_id)
    if user is None or not user.is_active:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=401, detail='Session is no longer valid')
    replacement = new_refresh_token()
    session.refresh_token_hash = digest(replacement)
    session.rotation_count += 1
    session.last_used_at = now
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return TokenResponse(access_token=create_access_token(str(user.id), user.role, session.id), refresh_token=replacement)


def get_current_staff_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]) -> StaffUser:
    failure = HTTPException(status_code=401, detail='Could not validate credentials', headers={'WWW-Authenticate': 'Bearer'})
    try:
        payload = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[ALGORITHM])
        subject, sid = payload.get('sub'), payload.get('sid')
        if (payload.get('type') != 'access' or not isinstance(subject, str) or not subject.isascii()
                or not subject.isdigit() or not isinstance(sid, str)):
            raise failure
    except InvalidTokenError:
        raise failure from None
    session = db.get(AuthSession, sid)
    if (session is None or session.staff_user_id != int(subject) or session.revoked_at is not None
            or utc(session.expires_at) <= datetime.now(timezone.utc)):
        raise failure
    user = db.get(StaffUser, int(subject))
    if user is None or not user.is_active:
        raise failure
    return user


@router.post('/logout', status_code=204)
def logout(data: LogoutRequest, db: Annotated[Session, Depends(get_db)]):
    # Accept refresh secret so logout still works if the access token expired.
    if data.refresh_token:
        session = db.scalar(select(AuthSession).where(AuthSession.refresh_token_hash == digest(data.refresh_token)).with_for_update())
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()


@router.post('/logout-all', status_code=204)
def logout_all(db: Annotated[Session, Depends(get_db)], current_user: Annotated[StaffUser, Depends(get_current_staff_user)]):
    revoke_user_sessions(db, current_user.id)
    db.commit()


@router.get('/me', response_model=StaffUserResponse)
def me(current_user: Annotated[StaffUser, Depends(get_current_staff_user)]):
    return current_user


@router.get('/sessions', response_model=list[AuthSessionResponse])
def list_sessions(db: Annotated[Session, Depends(get_db)], current_user: Annotated[StaffUser, Depends(get_current_staff_user)]):
    return db.scalars(select(AuthSession).where(AuthSession.staff_user_id == current_user.id).order_by(AuthSession.created_at.desc())).all()


@router.delete('/sessions/{session_id}', status_code=204)
def revoke_session(session_id: str, db: Annotated[Session, Depends(get_db)], current_user: Annotated[StaffUser, Depends(get_current_staff_user)]):
    session = db.scalar(select(AuthSession).where(AuthSession.id == session_id, AuthSession.staff_user_id == current_user.id).with_for_update())
    if session is None:
        raise HTTPException(status_code=404, detail='Session not found')
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()


def require_roles(*allowed_roles: str):
    def role_checker(current_user: Annotated[StaffUser, Depends(get_current_staff_user)]) -> StaffUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail='You do not have permission to perform this action')
        return current_user
    return role_checker
