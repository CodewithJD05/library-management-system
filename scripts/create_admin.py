import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.staff_user import StaffUser


def main():
    full_name = input("Admin full name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Admin password: ")
    confirm_password = getpass.getpass("Confirm password: ")

    if not full_name or not email or not password:
        print("Name, email, and password are required.")
        return

    if password != confirm_password:
        print("Passwords do not match.")
        return

    if len(password) < 12:
        print("Use a password with at least 12 characters.")
        return

    with SessionLocal() as db:
        existing_user = db.scalar(
            select(StaffUser).where(StaffUser.email == email)
        )

        if existing_user:
            print("A staff account with this email already exists.")
            return

        admin = StaffUser(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print(f"Administrator account created for {email}.")


if __name__ == "__main__":
    main()