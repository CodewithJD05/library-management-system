
from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db


app = FastAPI(
    title=settings.app_name,
    description="Backend API for managing library operations.",
    version="1.0.0",
)


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
