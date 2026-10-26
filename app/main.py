
from unittest import skipIf
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

from app.routers.books import router as books_router

from app.routers.members import router as members_router

from app.routers.borrowings import router as borrowings_router

from app.routers.book_copies import router as book_copies_router

from app.routers.dashboard import router as dashboard_router

from app.routers.fines import router as fines_router

app = FastAPI(
    title=settings.app_name,
    description="Backend API for managing library operations.",
    version="1.0.0"
)


app.include_router(books_router)
app.include_router(members_router)
app.include_router(borrowings_router)
app.include_router(book_copies_router)
app.include_router(fines_router)
app.include_router(dashboard_router)

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
def database_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }
