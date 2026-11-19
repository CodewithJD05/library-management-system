# Library Management System

A backend-focused Library Management System built with FastAPI and PostgreSQL, with a web-based frontend for managing library operations.

## Features

- User authentication and role-based access
- Book and physical book-copy management
- Member management
- Borrowing and book-return workflows
- Fine management
- Staff management
- REST API with interactive Swagger documentation
- Database migrations with Alembic
- Automated tests with pytest

## Technology Stack

- **Backend:** Python, FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Testing:** pytest
- **Frontend:** HTML, CSS, JavaScript
- **API Testing:** Postman

## Local Setup

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd library-management-system
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root using `.env.example` as a reference.

Set your PostgreSQL connection URL and a secure secret key. Do not commit your `.env` file or share credentials publicly.

### 5. Apply database migrations

```powershell
alembic upgrade head
```

### 6. Start the API server

```powershell
uvicorn app.main:app --reload
```

Open the following URLs in your browser:

- API: http://127.0.0.1:8000
- Swagger documentation: http://127.0.0.1:8000/docs
- ReDoc documentation: http://127.0.0.1:8000/redoc

## Running Tests

```powershell
pytest -q
```

## Project Status

This project is being developed as a practical portfolio project with an emphasis on maintainable code, database integrity, API validation, and automated testing.

## Security

- Keep `.env` out of version control.
- Use strong secret keys and passwords.
- Configure production environment variables separately from local development.

## November 2026 feature update

The existing API and frontend have been extended with:

- `super_admin`, `admin`, `librarian` staff permissions. Only Super Admin can manage admins; Admin can manage librarians; librarians cannot access staff administration. A database partial unique index permits **at most one** Super Admin. The Super Admin cannot be deleted, deactivated, or modified by the staff API.
- JWT access tokens (30 minutes) with hashed, **rotating** refresh tokens (default 7-day session lifetime), session revocation, logout and logout-all.
- Member categories: `student` and `faculty`. The existing members become `student` after migration. Daily rates come from `.env`: `STUDENT_DAILY_FINE=10`, `FACULTY_DAILY_FINE=5` (example policy—confirm with library management).
- A holiday calendar. Each completed 24-hour overdue block is charged using the local date on which it ends, excluding dates configured in `/holidays/`. The default zone is `Asia/Kolkata`. Weekends count unless manually added as holidays. Fines already assessed are not retroactively recalculated when holiday policy changes.
- A first-come-first-served reservation queue (`/reservations/`) for **active members**, entered by staff. Reservations are allowed when no physical copy is available for general borrowing. On return or adding a copy, the first waiting reservation receives a 48-hour hold. Other members cannot borrow the held copy. Expired holds are released on relevant requests and by the daily reminder script.
- Durable email outbox (`email_notifications`). Borrowing, return and reservation-ready emails are queued transactionally. Configured SMTP sends them after API responses; due reminders and expired holds are processed by a scheduled script. See `/notifications/` for delivery state.
- Updated frontend tabs for staff permissions, reservations, holiday calendar, sessions and email outbox.

### Upgrade an existing installation

**Back up your PostgreSQL database first.** In your activated virtual environment:

```powershell
python -m pip install -r requirements.txt
alembic upgrade head
python -m scripts.create_super_admin
uvicorn app.main:app --reload
```

Run `create_super_admin` **once**, after migrating. Your existing Admin/Librarian accounts remain in place. Do **not** initialize Alembic again or regenerate the migration. No data reset is required by the new migration.

The local frontend uses `http://127.0.0.1:8000` when served from `localhost:5500` or `127.0.0.1:5500`; other domains use the existing hosted API URL in `frontend/js/config.js`. **Deploy the updated backend before using the updated frontend against the hosted API.**

### Authentication endpoints

- `POST /auth/login`: form-encoded `username` and `password`; returns `access_token`, `refresh_token`, `token_type`.
- `POST /auth/refresh`: JSON `{"refresh_token":"..."}`; returns a rotated refresh token and new access token. Previous refresh token is immediately invalid.
- `POST /auth/logout`: JSON `{"refresh_token":"..."}`; revokes the current session even if access token expired.
- `POST /auth/logout-all`: bearer access token; invalidates all sessions for that staff user.
- `GET /auth/me`, `GET /auth/sessions`, `DELETE /auth/sessions/{session_id}`: bearer access token.

**Security note:** Browser tokens currently use `sessionStorage` for compatibility with the existing static frontend, not HttpOnly cookies. Enforce HTTPS, CSP, safe third-party scripts, and consider secure cookie-based refresh transport before a public production rollout. Never store raw refresh tokens in your database; only SHA-256 hashes are saved.

### Set up email delivery and due reminders

Add SMTP details to `.env` (use your mail provider's app password or SMTP credential, not your regular mailbox password):

```dotenv
SMTP_HOST=smtp.your-provider.example
SMTP_PORT=587
SMTP_USERNAME=your-account@example.com
SMTP_PASSWORD=your-smtp-app-password
SMTP_FROM_EMAIL=your-account@example.com
SMTP_USE_TLS=true
REMINDER_DAYS_BEFORE=1
```

For immediate borrowing, return and reservation alerts, the app queues email during the database transaction and attempts SMTP delivery in the background after committing. The outbox preserves failed messages for retries.

For **scheduled due reminders and expired reservation holds**, run this *once per day*, via Windows Task Scheduler, cron, or a hosted scheduled worker:

```powershell
python -m scripts.send_due_reminders
```

For local testing you may run this command manually, but due reminders will not run automatically until a scheduler is configured. Without SMTP configuration, email records remain queued but **no email is delivered**.

### Running tests

```powershell
pytest -q
```

The original tests were retained except three staff-permission expectations updated to match the new requirement (admins cannot demote or deactivate other admins). New feature tests cover refresh rotation, sessions, staff permissions, reservations, member categories, fine rates and notification queuing.

### Limitations / production checks

- **Confirm** student/faculty rates, holiday policy and reservation hold duration before using them with real members.
- Member reservation entry is staff-mediated. Public member self-service would require separate member authentication; the endpoint is intentionally not anonymous to prevent impersonation by member ID.
- Real PostgreSQL concurrency behavior and SMTP provider delivery still need verification in your deployment environment; SQLite unit tests alone do not prove these integration behaviors.
- Scheduled jobs need a real scheduler on the server. Running the web server alone does not create due reminders.
