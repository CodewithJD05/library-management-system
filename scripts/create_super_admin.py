"""Run once: python -m scripts.create_super_admin."""
import getpass
from sqlalchemy import select
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.staff_user import StaffUser


def main():
    name = input('Super Admin full name: ').strip()
    email = input('Super Admin email: ').strip().lower()
    password = getpass.getpass('Password (min 12 characters): ')
    confirmation = getpass.getpass('Confirm password: ')
    if len(name) < 2 or '@' not in email or len(password) < 12 or password != confirmation:
        raise SystemExit('Invalid name, email, or password confirmation')
    with SessionLocal.begin() as db:
        if db.scalar(select(StaffUser.id).where(StaffUser.role == 'super_admin')) is not None:
            raise SystemExit('Super Admin already exists. No second account can be created.')
        if db.scalar(select(StaffUser.id).where(StaffUser.email == email)) is not None:
            raise SystemExit('Email already exists')
        db.add(StaffUser(full_name=name, email=email, password_hash=hash_password(password), role='super_admin', is_active=True))
    print('Super Admin created successfully')

if __name__ == '__main__':
    main()
