from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    verify_password,
)
from app.db.session import get_db
from app.models.staff_user import StaffUser
from app.schemas.auth import TokenResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    staff_user = db.scalar(
        select(StaffUser).where(
            StaffUser.email == form_data.username.lower().strip()
        )
    )

    if (
        staff_user is None
        or not verify_password(
            form_data.password,
            staff_user.password_hash,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not staff_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff account is inactive",
        )

    access_token = create_access_token(
        subject=str(staff_user.id),
        role=staff_user.role,
    )

    return TokenResponse(access_token=access_token)


def get_current_staff_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> StaffUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[ALGORITHM],
        )
        subject = payload.get("sub")

        if (
            not isinstance(subject, str)
            or not subject.isascii()
            or not subject.isdigit()
        ):
            raise credentials_exception

        staff_user_id = int(subject)

    except InvalidTokenError:
        raise credentials_exception from None

    staff_user = db.get(StaffUser, staff_user_id)

    if staff_user is None or not staff_user.is_active:
        raise credentials_exception

    return staff_user


def require_roles(*allowed_roles: str):
    def role_checker(
        current_user: Annotated[
            StaffUser,
            Depends(get_current_staff_user),
        ],
    ) -> StaffUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )

        return current_user

    return role_checker