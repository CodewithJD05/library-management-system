
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.staff_user import StaffUser
from app.routers.auth import (
    get_current_staff_user,
    router as auth_router,
)
from app.routers.books import router as books_router
from app.routers.book_copies import router as book_copies_router
from app.routers.borrowings import router as borrowings_router
from app.routers.dashboard import router as dashboard_router
from app.routers.fines import router as fines_router
from app.routers.members import router as members_router
from app.routers.staff import router as staff_router


app = FastAPI(
    title=settings.app_name,
    description="Backend API for managing library operations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(auth_router)
app.include_router(books_router)
app.include_router(members_router)
app.include_router(borrowings_router)
app.include_router(book_copies_router)
app.include_router(fines_router)
app.include_router(dashboard_router)
app.include_router(staff_router)


@app.get("/")
def home():
    return {
        "message": "Library Management System API is running",
        "status": "success",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/health/db")
def database_health(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_staff_user),
):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }
