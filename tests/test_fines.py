
from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import get_db
from app.models.borrowing import Borrowing
from app.models.fine import Fine


@pytest.fixture()
def client(authenticated_client):
    return authenticated_client


def create_test_book(client):
    response = client.post(
        "/books/",
        json={
            "title": "Testing Python",
            "isbn": "FINE-ISBN-001",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_test_copy(client, book_id, barcode="FINE-COPY-001"):
    response = client.post(
        f"/books/{book_id}/copies",
        json={"barcode": barcode},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_test_member(client):
    response = client.post(
        "/members/",
        json={
            "full_name": "Fine Test Member",
            "email": "fine.test@example.com",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def set_due_date(client, borrowing_id, due_at):
    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        borrowing = db.get(Borrowing, borrowing_id)
        assert borrowing is not None
        borrowing.due_at = due_at
        db.commit()
    finally:
        db.close()


def create_overdue_return(
    client,
    barcode="FINE-COPY-001",
    days=3,
    book_id=None,
    member_id=None,
):
    if book_id is None:
        book_id = create_test_book(client)

    if member_id is None:
        member_id = create_test_member(client)

    copy_id = create_test_copy(client, book_id, barcode)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201, borrow_response.text
    borrowing_id = borrow_response.json()["id"]

    set_due_date(
        client,
        borrowing_id,
        datetime.now(timezone.utc) - timedelta(days=days, seconds=1),
    )

    return_response = client.put(
        f"/borrowings/{borrowing_id}/return"
    )
    assert return_response.status_code == 200, return_response.text

    return borrowing_id, return_response


def get_fine_for_borrowing(client, borrowing_id):
    response = client.get("/fines/")
    assert response.status_code == 200, response.text

    return next(
        (
            fine
            for fine in response.json()
            if fine["borrowing_id"] == borrowing_id
        ),
        None,
    )


def test_fine_is_zero_before_due_date(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )

    assert response.status_code == 201
    assert response.json()["fine_amount"] == 0


def test_overdue_borrowing_has_fine(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert response.status_code == 201
    borrowing_id = response.json()["id"]

    set_due_date(
        client,
        borrowing_id,
        datetime.now(timezone.utc) - timedelta(days=3, seconds=1),
    )

    response = client.get("/borrowings/")
    assert response.status_code == 200

    borrowing_data = next(
        item for item in response.json()
        if item["id"] == borrowing_id
    )
    assert borrowing_data["fine_amount"] == 30


def test_returned_borrowing_fine_stops_at_return_time(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert response.status_code == 201
    borrowing_id = response.json()["id"]

    set_due_date(
        client,
        borrowing_id,
        datetime.now(timezone.utc) - timedelta(days=3, seconds=1),
    )

    response = client.put(
        f"/borrowings/{borrowing_id}/return"
    )

    assert response.status_code == 200
    assert response.json()["fine_amount"] == 30


def test_late_return_creates_fine_record(client):
    borrowing_id, return_response = create_overdue_return(client)

    assert return_response.json()["fine_amount"] == 30

    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        fine = (
            db.query(Fine)
            .filter(Fine.borrowing_id == borrowing_id)
            .first()
        )

        assert fine is not None
        assert float(fine.amount) == 30.00
        assert float(fine.daily_rate) == 10.00
        assert fine.status == "unpaid"
        assert fine.assessed_at is not None
    finally:
        db.close()


def test_on_time_return_does_not_create_fine_record(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201
    borrowing_id = borrow_response.json()["id"]

    return_response = client.put(
        f"/borrowings/{borrowing_id}/return"
    )

    assert return_response.status_code == 200
    assert return_response.json()["fine_amount"] == 0

    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        fine = (
            db.query(Fine)
            .filter(Fine.borrowing_id == borrowing_id)
            .first()
        )
        assert fine is None
    finally:
        db.close()


def test_get_fines_returns_saved_fine(client):
    borrowing_id, _ = create_overdue_return(client)

    fine = get_fine_for_borrowing(client, borrowing_id)

    assert fine is not None
    assert fine["borrowing_id"] == borrowing_id
    assert fine["amount"] == 30.0
    assert fine["status"] == "unpaid"


def test_get_fines_unpaid_only(client):
    borrowing_id, _ = create_overdue_return(client)

    response = client.get("/fines/?unpaid_only=true")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["borrowing_id"] == borrowing_id
    assert response.json()[0]["status"] == "unpaid"


def test_pay_fine_successfully(client):
    borrowing_id, _ = create_overdue_return(client)
    fine = get_fine_for_borrowing(client, borrowing_id)
    assert fine is not None

    response = client.put(f"/fines/{fine['id']}/pay")

    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    assert response.json()["paid_at"] is not None
    assert response.json()["amount"] == 30.0


def test_cannot_pay_fine_twice(client):
    borrowing_id, _ = create_overdue_return(client)
    fine = get_fine_for_borrowing(client, borrowing_id)
    assert fine is not None

    first_response = client.put(f"/fines/{fine['id']}/pay")
    assert first_response.status_code == 200

    second_response = client.put(f"/fines/{fine['id']}/pay")
    assert second_response.status_code == 409


def test_pay_nonexistent_fine_returns_404(client):
    response = client.put("/fines/999999/pay")

    assert response.status_code == 404


def test_get_fines_pagination(client):
    book_id = create_test_book(client)
    member_id = create_test_member(client)

    first_borrowing_id, _ = create_overdue_return(
        client,
        barcode="FINE-PAGE-001",
        book_id=book_id,
        member_id=member_id,
    )
    second_borrowing_id, _ = create_overdue_return(
        client,
        barcode="FINE-PAGE-002",
        book_id=book_id,
        member_id=member_id,
    )

    first_fine = get_fine_for_borrowing(client, first_borrowing_id)
    second_fine = get_fine_for_borrowing(client, second_borrowing_id)
    assert first_fine is not None
    assert second_fine is not None

    response = client.get("/fines/?skip=0&limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1
    first_page_id = response.json()[0]["id"]

    response = client.get("/fines/?skip=1&limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] != first_page_id


def test_get_fines_filter_by_member(client):
    borrowing_id, _ = create_overdue_return(
        client,
        barcode="FINE-MEMBER-001",
    )

    response = client.get("/fines/?member_id=999999")
    assert response.status_code == 200
    assert response.json() == []

    borrowing_response = client.get("/borrowings/")
    assert borrowing_response.status_code == 200

    borrowing = next(
        item for item in borrowing_response.json()
        if item["id"] == borrowing_id
    )
    member_id = borrowing["member_id"]

    response = client.get(f"/fines/?member_id={member_id}")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["borrowing_id"] == borrowing_id


def test_get_fine_summary_with_no_fines(client):
    response = client.get("/fines/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_fines": 0,
        "unpaid_fines": 0,
        "paid_fines": 0,
        "total_amount": 0.0,
        "unpaid_amount": 0.0,
        "paid_amount": 0.0,
    }


def test_get_fine_summary_with_paid_and_unpaid_fines(client):
    book_id = create_test_book(client)
    member_id = create_test_member(client)

    first_borrowing_id, _ = create_overdue_return(
        client,
        barcode="SUMMARY-COPY-001",
        book_id=book_id,
        member_id=member_id,
    )
    second_borrowing_id, _ = create_overdue_return(
        client,
        barcode="SUMMARY-COPY-002",
        book_id=book_id,
        member_id=member_id,
    )

    first_fine = get_fine_for_borrowing(client, first_borrowing_id)
    second_fine = get_fine_for_borrowing(client, second_borrowing_id)
    assert first_fine is not None
    assert second_fine is not None

    payment_response = client.put(
        f"/fines/{first_fine['id']}/pay"
    )
    assert payment_response.status_code == 200

    response = client.get("/fines/summary")

    assert response.status_code == 200
    summary = response.json()

    assert summary["total_fines"] == 2
    assert summary["paid_fines"] == 1
    assert summary["unpaid_fines"] == 1
    assert summary["total_amount"] == (
        summary["paid_amount"] + summary["unpaid_amount"]
    )
    assert summary["paid_amount"] > 0
    assert summary["unpaid_amount"] > 0
