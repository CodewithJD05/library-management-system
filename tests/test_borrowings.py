from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import get_db
from app.models.borrowing import Borrowing


@pytest.fixture()
def client(authenticated_client):
    return authenticated_client


def create_test_book(client):
    response = client.post(
        "/books/",
        json={
            "title": "Testing Python",
            "isbn": "BORROW-ISBN-001",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_test_copy(client, book_id, barcode="BORROW-COPY-001"):
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
            "full_name": "Borrow Test Member",
            "email": "borrow.test@example.com",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def set_borrowing_due_date(client, borrowing_id, due_at):
    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        borrowing = db.get(Borrowing, borrowing_id)
        assert borrowing is not None
        borrowing.due_at = due_at
        db.commit()
    finally:
        db.close()


def test_borrow_return_and_borrow_again(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert response.status_code == 201
    borrowing_id = response.json()["id"]
    assert response.json()["returned_at"] is None

    duplicate_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert duplicate_response.status_code == 409

    return_response = client.put(f"/borrowings/{borrowing_id}/return")
    assert return_response.status_code == 200
    assert return_response.json()["returned_at"] is not None

    copies_response = client.get(f"/books/{book_id}/copies")
    assert copies_response.status_code == 200
    assert copies_response.json()[0]["status"] == "available"

    second_borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert second_borrow_response.status_code == 201


def test_different_copies_of_same_book_can_be_borrowed(client):
    book_id = create_test_book(client)
    first_copy_id = create_test_copy(client, book_id, "COPY-001")
    second_copy_id = create_test_copy(client, book_id, "COPY-002")
    member_id = create_test_member(client)

    first_response = client.post(
        "/borrowings/",
        json={"book_copy_id": first_copy_id, "member_id": member_id},
    )
    second_response = client.post(
        "/borrowings/",
        json={"book_copy_id": second_copy_id, "member_id": member_id},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    copies_response = client.get(f"/books/{book_id}/copies")
    assert copies_response.status_code == 200
    statuses = {
        copy["id"]: copy["status"]
        for copy in copies_response.json()
    }

    assert statuses[first_copy_id] == "borrowed"
    assert statuses[second_copy_id] == "borrowed"


def test_borrowing_nonexistent_copy_returns_404(client):
    member_id = create_test_member(client)

    response = client.post(
        "/borrowings/",
        json={"book_copy_id": 999999, "member_id": member_id},
    )

    assert response.status_code == 404


def test_borrowing_inactive_member_is_rejected(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    update_response = client.put(
        f"/members/{member_id}",
        json={"is_active": False},
    )
    assert update_response.status_code == 200

    response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert response.status_code == 400


def test_cannot_delete_book_with_borrowing_history(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    delete_response = client.delete(f"/books/{book_id}")
    assert delete_response.status_code == 409


def test_cannot_delete_member_with_borrowing_history(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    delete_response = client.delete(f"/members/{member_id}")
    assert delete_response.status_code == 409


def test_filter_active_borrowings(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    response = client.get("/borrowings/?active_only=true")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["returned_at"] is None


def test_filter_borrowings_by_member(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    response = client.get(f"/borrowings/?member_id={member_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["member_id"] == member_id


def test_filter_borrowings_by_catalogue_book(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    response = client.get(f"/borrowings/?book_id={book_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["book_copy_id"] == copy_id


def test_duplicate_copy_barcode_is_rejected(client):
    book_id = create_test_book(client)
    create_test_copy(client, book_id, "DUPLICATE-BARCODE")

    response = client.post(
        f"/books/{book_id}/copies",
        json={"barcode": "DUPLICATE-BARCODE"},
    )

    assert response.status_code == 409


def test_overdue_filter_excludes_borrowed_books_not_yet_due(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    response = client.get("/borrowings/?overdue_only=true")

    assert response.status_code == 200
    assert response.json() == []


def test_overdue_filter_includes_past_due_unreturned_borrowing(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201
    borrowing_id = borrow_response.json()["id"]

    set_borrowing_due_date(
        client,
        borrowing_id,
        datetime.now(timezone.utc) - timedelta(days=1),
    )

    response = client.get("/borrowings/?overdue_only=true")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == borrowing_id


def test_overdue_count_is_zero_when_no_borrowings_are_overdue(client):
    response = client.get("/borrowings/overdue/count")

    assert response.status_code == 200
    assert response.json() == {"overdue_count": 0}


def test_overdue_count_includes_past_due_unreturned_borrowing(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201
    borrowing_id = borrow_response.json()["id"]

    set_borrowing_due_date(
        client,
        borrowing_id,
        datetime.now(timezone.utc) - timedelta(days=1),
    )

    response = client.get("/borrowings/overdue/count")

    assert response.status_code == 200
    assert response.json() == {"overdue_count": 1}


def test_extend_borrowing_due_date(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201
    borrowing_id = borrow_response.json()["id"]

    new_due_at = (
        datetime.now(timezone.utc) + timedelta(days=30)
    ).isoformat()

    response = client.patch(
        f"/borrowings/{borrowing_id}/due-date",
        json={"due_at": new_due_at},
    )

    assert response.status_code == 200
    assert response.json()["due_at"] is not None


def test_cannot_extend_returned_borrowing(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201
    borrowing_id = borrow_response.json()["id"]

    return_response = client.put(f"/borrowings/{borrowing_id}/return")
    assert return_response.status_code == 200

    new_due_at = (
        datetime.now(timezone.utc) + timedelta(days=30)
    ).isoformat()

    response = client.patch(
        f"/borrowings/{borrowing_id}/due-date",
        json={"due_at": new_due_at},
    )

    assert response.status_code == 409


def test_cannot_set_due_date_in_the_past(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201
    borrowing_id = borrow_response.json()["id"]

    past_due_at = (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).isoformat()

    response = client.patch(
        f"/borrowings/{borrowing_id}/due-date",
        json={"due_at": past_due_at},
    )

    assert response.status_code == 422


def test_member_borrowing_history_returns_records(client):
    book_id = create_test_book(client)
    create_test_copy(client, book_id, barcode="HISTORY-COPY-001")
    member_id = create_test_member(client)

    copy_id = client.get(
        f"/books/{book_id}/copies"
    ).json()[0]["id"]

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    response = client.get(f"/members/{member_id}/borrowings")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["member_id"] == member_id


def test_member_borrowing_history_returns_empty_list(client):
    member_id = create_test_member(client)

    response = client.get(f"/members/{member_id}/borrowings")

    assert response.status_code == 200
    assert response.json() == []


def test_member_borrowing_history_for_missing_member_returns_404(client):
    response = client.get("/members/99999/borrowings")

    assert response.status_code == 404


def test_member_borrowing_history_supports_pagination(client):
    book_id = create_test_book(client)
    member_id = create_test_member(client)

    create_test_copy(client, book_id, barcode="HISTORY-PAGE-001")
    create_test_copy(client, book_id, barcode="HISTORY-PAGE-002")

    copies = client.get(f"/books/{book_id}/copies").json()

    for copy in copies:
        borrow_response = client.post(
            "/borrowings/",
            json={
                "book_copy_id": copy["id"],
                "member_id": member_id,
            },
        )
        assert borrow_response.status_code == 201

    response = client.get(
        f"/members/{member_id}/borrowings?skip=0&limit=1"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.get(
        f"/members/{member_id}/borrowings?skip=1&limit=1"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_cannot_return_borrowing_twice(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201
    borrowing_id = borrow_response.json()["id"]

    first_return = client.put(
        f"/borrowings/{borrowing_id}/return"
    )
    second_return = client.put(
        f"/borrowings/{borrowing_id}/return"
    )

    assert first_return.status_code == 200
    assert second_return.status_code == 409



def test_database_rejects_duplicate_active_borrowing(client):
    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    first_response = client.post(
        "/borrowings/",
        json={
            "book_copy_id": copy_id,
            "member_id": member_id,
        },
    )
    assert first_response.status_code == 201

    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())

    try:
        duplicate = Borrowing(
            book_copy_id=copy_id,
            member_id=member_id,
        )
        db.add(duplicate)

        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()
