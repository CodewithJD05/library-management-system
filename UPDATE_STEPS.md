# Apply the Library Management update

1. Back up your PostgreSQL database and your project folder. Keep your real `.env` file unchanged; it is not included in this archive.
2. Replace the existing project files with the files from this archive; the folder structure must remain `app/`, `migrations/`, `frontend/`, etc.
3. Activate the existing virtual environment and install requirements only if needed: `python -m pip install -r requirements.txt`.
4. Add/update the policy/SMTP values in `.env` as needed. The suggested policies are **student ₹10/day**, **faculty ₹5/day**, **48-hour reservation holds**, **1-day due reminders**, and **7-day refresh sessions**. Confirm policy before production use.
5. Run `alembic upgrade head` (do NOT run `alembic init` and do NOT regenerate the migration).
6. Run `python -m scripts.create_super_admin` once to create the protected root account.
7. Run `pytest -q` and then `uvicorn app.main:app --reload`.
8. Start the frontend with Live Server from `frontend/index.html` on port 5500. The local frontend now calls `http://127.0.0.1:8000` automatically.
9. Configure SMTP in `.env` for real emails, and schedule `python -m scripts.send_due_reminders` daily using Windows Task Scheduler or your hosting scheduler. An email queue alone does NOT send emails without SMTP.
10. For the hosted site, deploy the updated backend with migrations before deploying the updated frontend.

**Safety:** For a real production system, verify PostgreSQL concurrency behavior and real SMTP sending on a test/staging environment before a live release. This code was tested against SQLite for Python integration tests and schema migration and Postgres SQL was generated, but a live Postgres/SMTP server was not available in the test environment.

**Auth change:** Old pre-update JWTs have no session ID and are intentionally rejected; users must sign in again once after upgrading.

**Reservation access:** Reservations are placed by authorized library staff for any active registered member. Anonymous public reservations are not offered, because a member ID alone is not a secure way to establish identity.
