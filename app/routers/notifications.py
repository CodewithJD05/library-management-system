"""Admin visibility into durable outbound notification delivery."""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.email_notification import EmailNotification
from app.models.staff_user import StaffUser
from app.routers.auth import require_roles
from app.services.notifications import email_enabled, deliver_queued_notifications

router = APIRouter(prefix='/notifications', tags=['Email Notifications'])
DB = Annotated[Session, Depends(get_db)]
Admin = Annotated[StaffUser, Depends(require_roles('admin','super_admin'))]

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_key: str
    recipient: str
    subject: str
    status: str
    attempts: int
    created_at: datetime
    sent_at: datetime | None
    last_error: str | None

@router.get('/', response_model=list[NotificationResponse])
def list_notifications(db: DB, current_user: Admin, status: str | None = None,
                       skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    query = select(EmailNotification)
    if status is not None:
        if status not in {'pending', 'sent', 'failed'}:
            raise HTTPException(status_code=422, detail='Invalid delivery status')
        query = query.where(EmailNotification.status == status)
    return db.scalars(query.order_by(EmailNotification.id.desc()).offset(skip).limit(limit)).all()

@router.get('/summary')
def notification_summary(db: DB, current_user: Admin):
    return {'pending': db.scalar(select(func.count()).select_from(EmailNotification).where(EmailNotification.status=='pending')),
            'sent': db.scalar(select(func.count()).select_from(EmailNotification).where(EmailNotification.status=='sent')),
            'failed': db.scalar(select(func.count()).select_from(EmailNotification).where(EmailNotification.status=='failed')),
            'smtp_configured': email_enabled()}

@router.post('/dispatch', status_code=202)
def dispatch_notifications(background_tasks: BackgroundTasks, db: DB, current_user: Admin):
    if not email_enabled():
        raise HTTPException(status_code=503, detail='SMTP_HOST and SMTP_FROM_EMAIL must be configured')
    background_tasks.add_task(deliver_queued_notifications)
    return {'message': 'Email dispatch queued'}
