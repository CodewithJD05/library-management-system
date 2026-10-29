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
