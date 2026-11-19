"""Staff management. Authorization is enforced server-side, not by UI controls."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.staff_user import StaffUser
from app.routers.auth import require_roles, revoke_user_sessions
from app.schemas.staff import StaffUserCreate, StaffUserResponse, StaffUserStatusUpdate, StaffUserUpdate

router = APIRouter(prefix='/staff', tags=['Staff Management'])
Manager = Annotated[StaffUser, Depends(require_roles('admin', 'super_admin'))]
DatabaseSession = Annotated[Session, Depends(get_db)]


def ensure_another_active_admin_exists(db: Session, staff_user: StaffUser) -> None:
    """A system without a super admin must retain one active admin."""
    if staff_user.role != 'admin' or not staff_user.is_active:
        return
    if db.scalar(select(StaffUser.id).where(StaffUser.role == 'super_admin', StaffUser.is_active.is_(True))) is not None:
        return
    count = db.scalar(select(func.count()).select_from(StaffUser).where(StaffUser.role == 'admin', StaffUser.is_active.is_(True)))
    if count <= 1:
        raise HTTPException(status_code=400, detail='Cannot remove the last active administrator')


def ensure_can_manage(actor: StaffUser, target: StaffUser, *, is_update: bool = False, changes: dict | None = None):
    if target.role == 'super_admin':
        raise HTTPException(status_code=403, detail='Super Admin cannot be modified, deactivated, or deleted')
    if actor.role == 'super_admin':
        return
    if target.role == 'admin':
        if is_update and actor.id == target.id and changes and not {'role', 'is_active'} & changes.keys():
            return  # Editing own profile or password only
        raise HTTPException(status_code=403, detail='Admin cannot manage other admins or deactivate/delete an admin')
    if changes and changes.get('role', 'librarian') != 'librarian':
        raise HTTPException(status_code=403, detail='Only Super Admin may promote staff to admin')


@router.post('/', response_model=StaffUserResponse, status_code=201)
def create_staff_user(staff_data: StaffUserCreate, db: DatabaseSession, current_user: Manager):
    if staff_data.role != 'librarian' and current_user.role != 'super_admin':
        raise HTTPException(status_code=403, detail='Only Super Admin may create administrators')
    if db.scalar(select(StaffUser.id).where(StaffUser.email == staff_data.email)) is not None:
        raise HTTPException(status_code=409, detail='A staff account with this email already exists')
    staff = StaffUser(full_name=staff_data.full_name, email=staff_data.email, password_hash=hash_password(staff_data.password), role=staff_data.role, is_active=True)
    db.add(staff)
    try:
        db.commit()
        db.refresh(staff)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Could not create staff account; check for duplicate email') from None
    return staff


@router.get('/', response_model=list[StaffUserResponse])
def list_staff_users(db: DatabaseSession, current_user: Manager, skip: int = 0, limit: int = 100):
    if skip < 0 or limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail='Invalid pagination parameters')
    return db.scalars(select(StaffUser).order_by(StaffUser.id).offset(skip).limit(limit)).all()


@router.get('/{staff_id}', response_model=StaffUserResponse)
def get_staff_user(staff_id: int, db: DatabaseSession, current_user: Manager):
    staff = db.get(StaffUser, staff_id)
    if staff is None:
        raise HTTPException(status_code=404, detail='Staff account not found')
    return staff


@router.patch('/{staff_id}', response_model=StaffUserResponse)
def update_staff_user(staff_id: int, staff_data: StaffUserUpdate, db: DatabaseSession, current_user: Manager):
    staff = db.scalar(select(StaffUser).where(StaffUser.id == staff_id).with_for_update())
    if staff is None:
        raise HTTPException(status_code=404, detail='Staff account not found')
    changes = staff_data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail='Provide at least one field to update')
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail='Staff fields cannot be null')
    ensure_can_manage(current_user, staff, is_update=True, changes=changes)
    if changes.get('role') == 'librarian' and staff.role == 'admin':
        ensure_another_active_admin_exists(db, staff)
    if 'email' in changes and db.scalar(select(StaffUser.id).where(StaffUser.email == changes['email'], StaffUser.id != staff_id)) is not None:
        raise HTTPException(status_code=409, detail='A staff account with this email already exists')
    if 'password' in changes:
        changes['password_hash'] = hash_password(changes.pop('password'))
        revoke_user_sessions(db, staff.id)
    for field, value in changes.items():
        setattr(staff, field, value)
    if 'role' in changes:
        revoke_user_sessions(db, staff.id)
    try:
        db.commit()
        db.refresh(staff)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Could not update staff account') from None
    return staff


@router.patch('/{staff_id}/status', response_model=StaffUserResponse)
def update_staff_status(staff_id: int, status_data: StaffUserStatusUpdate, db: DatabaseSession, current_user: Manager):
    staff = db.scalar(select(StaffUser).where(StaffUser.id == staff_id).with_for_update())
    if staff is None:
        raise HTTPException(status_code=404, detail='Staff account not found')
    ensure_can_manage(current_user, staff)
    if not status_data.is_active:
        ensure_another_active_admin_exists(db, staff)
        if staff.id == current_user.id:
            raise HTTPException(status_code=400, detail='You cannot deactivate your own account')
        revoke_user_sessions(db, staff.id)
    staff.is_active = status_data.is_active
    db.commit()
    db.refresh(staff)
    return staff


@router.delete('/{staff_id}', status_code=204)
def delete_staff_user(staff_id: int, db: DatabaseSession, current_user: Manager):
    target = db.scalar(select(StaffUser).where(StaffUser.id == staff_id).with_for_update())
    if target is None:
        raise HTTPException(status_code=404, detail='Staff account not found')
    ensure_can_manage(current_user, target)
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail='You cannot delete your own account')
    ensure_another_active_admin_exists(db, target)
    db.query(AuthSession).filter(AuthSession.staff_user_id == target.id).delete(synchronize_session=False)
    db.delete(target)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Cannot delete a staff account referenced by existing records') from None
