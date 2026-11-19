from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import settings
from app.models.holiday import Holiday
from app.models.staff_user import StaffUser
from app.routers.auth import get_current_staff_user, require_roles

router = APIRouter(prefix='/holidays', tags=['Holiday Calendar'])
DB = Annotated[Session, Depends(get_db)]
Staff = Annotated[StaffUser, Depends(get_current_staff_user)]
Admin = Annotated[StaffUser, Depends(require_roles('admin', 'super_admin'))]

class HolidayInput(BaseModel):
    day: date
    name: str = Field(min_length=2, max_length=150)

class HolidayOutput(HolidayInput):
    model_config = ConfigDict(from_attributes=True)
    id: int

@router.get('/policy')
def fine_policy(current_user: Staff):
    return {'student_daily_fine': settings.student_daily_fine,
            'faculty_daily_fine': settings.faculty_daily_fine,
            'library_timezone': settings.library_timezone,
            'holiday_policy': 'Completed 24-hour overdue periods; exclude periods ending on a configured holiday'}

@router.get('/', response_model=list[HolidayOutput])
def list_holidays(db: DB, current_user: Staff, year: int | None = None):
    query = select(Holiday).order_by(Holiday.day)
    if year is not None:
        if year < 1900 or year > 2200:
            raise HTTPException(status_code=422, detail='Invalid year')
        query = query.where(Holiday.day >= date(year, 1, 1), Holiday.day <= date(year, 12, 31))
    return db.scalars(query).all()

@router.post('/', response_model=HolidayOutput, status_code=201)
def add_holiday(data: HolidayInput, db: DB, current_user: Admin):
    holiday = Holiday(**data.model_dump())
    db.add(holiday)
    try:
        db.commit(); db.refresh(holiday)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail='Holiday already exists') from None
    return holiday

@router.delete('/{holiday_id}', status_code=204)
def delete_holiday(holiday_id: int, db: DB, current_user: Admin):
    holiday = db.get(Holiday, holiday_id)
    if holiday is None:
        raise HTTPException(status_code=404, detail='Holiday not found')
    db.delete(holiday); db.commit()
