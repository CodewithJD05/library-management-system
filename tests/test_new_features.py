"""Regression tests for staff hierarchy, refresh sessions, fines and reservations."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.core.security import hash_password
from app.models.staff_user import StaffUser
from app.models.borrowing import Borrowing
from app.models.fine import Fine
from app.models.email_notification import EmailNotification
from app.models.reservation import Reservation
from app.routers.auth import issue_tokens
from app.services.notifications import queue_due_reminders, process_pending_notifications
from app.utils.fine_calculator import calculate_fine

@pytest.fixture()
def client(authenticated_client):
    return authenticated_client


def add_staff(db, email, role):
    staff = StaffUser(full_name='Staff Test', email=email,
                      password_hash=hash_password('LongSecretPassword!'), role=role, is_active=True)
    db.add(staff)
    db.commit();db.refresh(staff)
    return staff


def use_staff(client, db, role, name='user'):
    staff = add_staff(db, f'{name}@test.com', role)
    pair = issue_tokens(db, staff)
    client.headers.update({'Authorization': f'Bearer {pair.access_token}'})
    return staff, pair


def setup_library(client, category='student'):
    book = client.post('/books/', json={'title':'Book Demo','isbn':'BOOK-DEMO-002'});
    assert book.status_code == 201, book.text
    book_id = book.json()['id']
    copy = client.post(f'/books/{book_id}/copies', json={'barcode':'BARCODE-DEMO-002'});
    assert copy.status_code == 201, copy.text
    member = client.post('/members/',json={'full_name':'Primary Member','email':'primary@test.com','category':category});
    assert member.status_code == 201, member.text
    other = client.post('/members/',json={'full_name':'Second Member','email':'second@test.com','category':'faculty'});
    assert other.status_code == 201, other.text
    return book_id, copy.json()['id'], member.json()['id'], other.json()['id']


def test_login_refresh_rotation_and_logout(client, db_session):
    add_staff(db_session,'login@test.com','librarian')
    login = client.post('/auth/login', data={'username':'login@test.com','password':'LongSecretPassword!'})
    assert login.status_code == 200
    first = login.json()
    assert first['refresh_token'] != first['access_token']
    client.headers.update({'Authorization':f"Bearer {first['access_token']}"})
    assert client.get('/auth/me').status_code == 200
    rotated = client.post('/auth/refresh',json={'refresh_token':first['refresh_token']})
    assert rotated.status_code == 200
    second = rotated.json()
    assert first['refresh_token'] != second['refresh_token']
    assert client.post('/auth/refresh',json={'refresh_token':first['refresh_token']}).status_code == 401
    assert client.post('/auth/logout',json={'refresh_token':second['refresh_token']}).status_code == 204
    client.headers.update({'Authorization':f"Bearer {second['access_token']}"})
    assert client.get('/auth/me').status_code == 401
    assert client.post('/auth/refresh',json={'refresh_token':second['refresh_token']}).status_code == 401


def test_access_token_without_session_rejected(client, db_session):
    from app.core.security import create_access_token
    staff = add_staff(db_session,'legacy@test.com','librarian')
    token = create_access_token(str(staff.id),staff.role)
    client.headers.update({'Authorization':f'Bearer {token}'})
    assert client.get('/auth/me').status_code == 401


def test_super_admin_staff_permissions(client, db_session):
    super_admin, _ = use_staff(client, db_session, 'super_admin', 'super')
    assert client.post('/staff/',json={'full_name':'Admin Two','email':'admin2@test.com',
                                      'password':'LongSecretPassword!','role':'admin'}).status_code == 201
    lib = client.post('/staff/',json={'full_name':'Library User','email':'lib2@test.com',
                                     'password':'LongSecretPassword!','role':'librarian'}).json()
    assert client.delete(f'/staff/{super_admin.id}').status_code == 403
    assert client.patch(f'/staff/{super_admin.id}/status',json={'is_active':False}).status_code == 403
    assert client.delete(f'/staff/{lib["id"]}').status_code == 204
    admin = db_session.scalar(select(StaffUser).where(StaffUser.email == 'admin2@test.com'))
    _, pair = use_staff(client,db_session,'admin','manager')
    assert client.delete(f'/staff/{admin.id}').status_code == 403
    assert client.patch(f'/staff/{admin.id}/status',json={'is_active':False}).status_code == 403
    assert client.post('/staff/',json={'full_name':'Sneaky Admin','email':'sneaky@test.com',
                                      'password':'LongSecretPassword!','role':'admin'}).status_code == 403
    # Librarians can't inspect staff management endpoints.
    use_staff(client, db_session,'librarian','reader')
    assert client.get('/staff/').status_code == 403


def test_single_super_admin_constraint(client, db_session):
    add_staff(db_session,'firstsuper@test.com','super_admin')
    second = StaffUser(full_name='Second Super',email='secondsuper@test.com',
                       password_hash='test-hash',role='super_admin',is_active=True)
    db_session.add(second)
    with pytest.raises(IntegrityError): db_session.commit()
    db_session.rollback()


def test_member_category_and_holiday_policy(client):
    book, copy, student, faculty = setup_library(client,'student')
    assert client.get(f'/members/{faculty}').json()['category']=='faculty'
    assert client.put(f'/members/{faculty}',json={'category':'unknown'}).status_code == 422
    due = datetime.now(timezone.utc) - timedelta(days=2, minutes=3)
    holiday = (due+timedelta(days=1)).astimezone(__import__('zoneinfo').ZoneInfo('Asia/Kolkata')).date()
    result = client.post('/holidays/',json={'day':holiday.isoformat(),'name':'Test Public Holiday'})
    assert result.status_code == 403  # Librarian cannot configure billing holidays.
    # Fine calculator respects a configured holiday over two completed overdue periods.
    assert calculate_fine(due, datetime.now(timezone.utc), 10, {holiday}) == 10
    assert calculate_fine(due, datetime.now(timezone.utc), 5, {holiday}) == 5


def test_faculty_discount_applied_on_return(client, db_session):
    book, copy, student, faculty = setup_library(client, 'student')
    borrow = client.post('/borrowings/',json={'book_copy_id':copy,'member_id':faculty})
    assert borrow.status_code == 201,borrow.text
    borrowing = db_session.get(Borrowing,borrow.json()['id'])
    borrowing.due_at = datetime.now(timezone.utc) - timedelta(days=2, minutes=2)
    db_session.commit()
    result = client.put(f'/borrowings/{borrowing.id}/return')
    assert result.status_code == 200,result.text
    assert result.json()['fine_amount'] == 10
    fine = db_session.scalar(select(Fine).where(Fine.borrowing_id == borrowing.id))
    assert fine.daily_rate == Decimal('5.00')
    assert fine.amount == Decimal('10.00')


def test_reservation_handoff_and_notification_queue(client, db_session):
    book, copy, holder, waiter = setup_library(client)
    assert client.post('/reservations/',json={'book_id':book,'member_id':waiter}).status_code == 409
    first = client.post('/borrowings/',json={'book_copy_id':copy,'member_id':holder})
    assert first.status_code == 201,first.text
    reserve = client.post('/reservations/',json={'book_id':book,'member_id':waiter})
    assert reserve.status_code == 201,reserve.text
    rid=reserve.json()['id'];assert reserve.json()['status']=='waiting'
    assert client.post('/reservations/',json={'book_id':book,'member_id':waiter}).status_code == 409
    returned=client.put(f"/borrowings/{first.json()['id']}/return")
    assert returned.status_code == 200,returned.text
    res=db_session.get(Reservation,rid)
    assert res.status=='ready'; assert res.book_copy_id==copy
    assert client.post('/borrowings/',json={'book_copy_id':copy,'member_id':holder}).status_code == 409
    eligible = client.post('/borrowings/',json={'book_copy_id':copy,'member_id':waiter})
    assert eligible.status_code == 201, eligible.text
    db_session.refresh(res);assert res.status=='fulfilled'
    assert db_session.scalar(select(EmailNotification).where(EmailNotification.event_key==f'reservation-ready-{rid}'))


def test_reservation_cancellation_releases_hold(client, db_session):
    book,copy,holder,waiter=setup_library(client)
    first=client.post('/borrowings/',json={'book_copy_id':copy,'member_id':holder})
    r=client.post('/reservations/',json={'book_id':book,'member_id':waiter}).json()
    client.put(f"/borrowings/{first.json()['id']}/return")
    cancel=client.post(f"/reservations/{r['id']}/cancel")
    assert cancel.status_code==200;assert cancel.json()['status']=='cancelled'
    assert client.post('/borrowings/',json={'book_copy_id':copy,'member_id':holder}).status_code==201


def test_due_reminder_outbox_is_idempotent(client, db_session):
    book,copy,member,_=setup_library(client)
    borrowing=client.post('/borrowings/',json={'book_copy_id':copy,'member_id':member})
    b=db_session.get(Borrowing,borrowing.json()['id']);b.due_at=datetime.now(timezone.utc)+timedelta(hours=8);db_session.commit()
    assert queue_due_reminders(db_session)==1
    assert queue_due_reminders(db_session)==0
    due_reminders=db_session.scalars(select(EmailNotification).where(EmailNotification.event_key.like('due-reminder-%'))).all()
    assert len(due_reminders)==1
    assert process_pending_notifications(db_session)==0  # SMTP not configured in test environment


def test_admin_can_manage_librarian_but_not_admin(client, db_session):
    admin, _ = use_staff(client, db_session, 'admin', 'adminstaff')
    lib = client.post('/staff/', json={'full_name':'Other Librarian','email':'otherlib@test.com',
                         'password':'LongSecretPassword!','role':'librarian'}).json()
    deactivate = client.patch(f"/staff/{lib['id']}/status",json={'is_active':False})
    assert deactivate.status_code==200
    assert deactivate.json()['is_active'] is False
    assert client.delete(f"/staff/{lib['id']}").status_code==204
    assert client.patch(f'/staff/{admin.id}', json={'role':'librarian'}).status_code==403


def test_super_admin_can_deactivate_and_delete_admin(client, db_session):
    super_admin,_ = use_staff(client, db_session, 'super_admin', 'root')
    admin = client.post('/staff/', json={'full_name':'Manager Admin','email':'manager@test.com',
                        'password':'LongSecretPassword!','role':'admin'}).json()
    assert client.patch(f"/staff/{admin['id']}/status",json={'is_active':False}).status_code==200
    assert client.delete(f"/staff/{admin['id']}").status_code==204
    assert client.get(f"/staff/{admin['id']}").status_code==404
    assert client.post('/staff/',json={'full_name':'Second Root','email':'root2@test.com',
                        'password':'LongSecretPassword!','role':'super_admin'}).status_code==422


def test_logout_all_revokes_every_access_token(client, db_session):
    staff = add_staff(db_session, 'all@test.com', 'librarian')
    first = issue_tokens(db_session, staff)
    second = issue_tokens(db_session, staff)
    client.headers.update({'Authorization':f'Bearer {first.access_token}'})
    assert len(client.get('/auth/sessions').json()) >= 2
    assert client.post('/auth/logout-all').status_code==204
    assert client.get('/auth/me').status_code==401
    client.headers.update({'Authorization':f'Bearer {second.access_token}'})
    assert client.get('/auth/me').status_code==401


def test_reservation_queue_fifo_on_cancellation(client, db_session):
    book,copy,borrower,first_waiter = setup_library(client)
    second_waiter = client.post('/members/', json={'full_name':'Third Member',
                                                   'email':'third@test.com','category':'faculty'}).json()['id']
    first = client.post('/borrowings/',json={'book_copy_id':copy,'member_id':borrower})
    a = client.post('/reservations/', json={'book_id':book,'member_id':first_waiter}).json()
    b = client.post('/reservations/', json={'book_id':book,'member_id':second_waiter}).json()
    assert client.put(f"/borrowings/{first.json()['id']}/return").status_code == 200
    assert client.get(f'/reservations/?book_id={book}').json()[1]['status'] == 'ready'
    assert client.post(f"/reservations/{a['id']}/cancel").status_code==200
    rows = {r['id']:r for r in client.get(f'/reservations/?book_id={book}').json()}
    assert rows[a['id']]['status']=='cancelled'
    assert rows[b['id']]['status']=='ready'
    assert rows[b['id']]['book_copy_id']==copy


def test_new_copy_allocated_to_waiting_reservation(client, db_session):
    book,copy,borrower,waiter=setup_library(client)
    first = client.post('/borrowings/',json={'book_copy_id':copy,'member_id':borrower})
    assert first.status_code == 201
    reserve = client.post('/reservations/',json={'book_id':book,'member_id':waiter}).json()
    new_copy=client.post(f'/books/{book}/copies', json={'barcode':'OTHER-COPY-2'})
    assert new_copy.status_code==201,new_copy.text
    assert db_session.get(Reservation,reserve['id']).status=='ready'
    assert client.post('/borrowings/',json={'book_copy_id':new_copy.json()['id'],
                                            'member_id':borrower}).status_code == 409


def test_configured_holiday_changes_recorded_student_fine(client, db_session):
    admin,_=use_staff(client,db_session,'admin','holiday-admin')
    book,copy,student,_ = setup_library(client)
    loan = client.post('/borrowings/',json={'book_copy_id':copy,'member_id':student})
    borrowing=db_session.get(Borrowing,loan.json()['id'])
    due=datetime.now(timezone.utc)-timedelta(days=2, minutes=5)
    borrowing.due_at=due
    db_session.commit()
    from zoneinfo import ZoneInfo
    holiday=(due + timedelta(days=1)).astimezone(ZoneInfo('Asia/Kolkata')).date()
    create=client.post('/holidays/',json={'day':holiday.isoformat(),'name':'Local Holiday'})
    assert create.status_code==201,create.text
    assert client.post('/holidays/',json={'day':holiday.isoformat(),'name':'Duplicate'}).status_code==409
    result=client.put(f'/borrowings/{borrowing.id}/return')
    assert result.status_code==200,result.text
    assert result.json()['fine_amount']==10
    fine=db_session.scalar(select(Fine).where(Fine.borrowing_id==borrowing.id))
    assert fine.amount==Decimal('10.00')
    assert client.get('/holidays/policy').json()['student_daily_fine']==10
    assert client.get('/notifications/summary').status_code==200
    assert client.get('/notifications/?status=nonexistent').status_code==422


def test_librarian_cannot_view_email_notifications(client):
    assert client.get('/notifications/').status_code==403
    assert client.get('/notifications/summary').status_code==403
    assert client.post('/notifications/dispatch').status_code==403
