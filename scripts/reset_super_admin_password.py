import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.staff_user import StaffUser
from app.routers.auth import revoke_user_sessions


def main():
    password = getpass.getpass("Enter new password: ")
    confirm = getpass.getpass("Confirm new password: ")

    if len(password) < 12:
        print("Password must contain at least 12 characters.")
        return

    if password != confirm:
        print("Passwords do not match.")
        return

    with SessionLocal.begin() as db:
        super_admin = db.scalar(
            select(StaffUser)
            .where(StaffUser.role == "super_admin")
            .with_for_update()
        )

        if super_admin is None:
            print("Super Admin account not found.")
            return

        super_admin.password_hash = hash_password(password)

        # Log out existing sessions for security
        revoke_user_sessions(db, super_admin.id)

    print("Super Admin password updated successfully.")


if __name__ == "__main__":
    main()