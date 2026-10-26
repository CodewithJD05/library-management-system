from datetime import datetime, timedelta, timezone
from app.models.borrowing import Borrowing
from app.models.fine import Fine



def create_test_book(client):
    response = client.post(
        "/books/",
        json={
            "title": "Testing Python",
            "isbn": "BORROW-ISBN-001",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_test_copy(client, book_id, barcode="BORROW-COPY-001"):
    response = client.post(
        f"/books/{book_id}/copies",
        json={"barcode": barcode},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_test_member(client):
    response = client.post(
        "/members/",
        json={
            "full_name": "Borrow Test Member",
            "email": "borrow.test@example.com",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


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
    statuses = {copy["id"]: copy["status"] for copy in copies_response.json()}

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

    # Set the due date in the past for this test.
    from app.db.session import get_db

    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        borrowing = db.get(Borrowing, borrowing_id)
        borrowing.due_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    finally:
        db.close()

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

    from app.db.session import get_db

    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        borrowing = db.get(Borrowing, borrowing_id)
        borrowing.due_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    finally:
        db.close()

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
    new_due_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

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

    new_due_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

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
    past_due_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    response = client.patch(
        f"/borrowings/{borrowing_id}/due-date",
        json={"due_at": past_due_at},
    )

    assert response.status_code == 422



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

    # Make the due date 3 complete days in the past.
    from app.db.session import get_db
    from app.models.borrowing import Borrowing
    from datetime import datetime, timedelta, timezone

    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())

    try:
        borrowing = db.get(Borrowing, borrowing_id)
        borrowing.due_at = datetime.now(timezone.utc) - timedelta(days=3, seconds=1)
        db.commit()
    finally:
        db.close()

    response = client.get("/borrowings/")

    assert response.status_code == 200
    borrowing_data = next(
        item for item in response.json() if item["id"] == borrowing_id
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

    from app.db.session import get_db
    from app.models.borrowing import Borrowing
    from datetime import datetime, timedelta, timezone

    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())

    try:
        borrowing = db.get(Borrowing, borrowing_id)
        borrowing.due_at = datetime.now(timezone.utc) - timedelta(days=3, seconds=1)
        db.commit()
    finally:
        db.close()

    response = client.put(f"/borrowings/{borrowing_id}/return")
    assert response.status_code == 200
    assert response.json()["fine_amount"] == 30




def test_late_return_creates_fine_record(client):
    from app.db.session import get_db

    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    borrowing_id = borrow_response.json()["id"]

    # Make the due date three complete days in the past.
    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        borrowing = db.get(Borrowing, borrowing_id)
        borrowing.due_at = datetime.now(timezone.utc) - timedelta(
            days=3, seconds=1
        )
        db.commit()
    finally:
        db.close()

    # Return the overdue book.
    return_response = client.put(
        f"/borrowings/{borrowing_id}/return"
    )
    assert return_response.status_code == 200
    assert return_response.json()["fine_amount"] == 30

    # Verify the permanent fine record in the database.
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
    from app.db.session import get_db

    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    borrowing_id = borrow_response.json()["id"]

    # The default due date is 15 days in the future.
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
    from app.db.session import get_db
    from app.models.fine import Fine

    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    borrowing_id = borrow_response.json()["id"]

    # Make the borrowing overdue by three complete days.
    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        borrowing = db.get(Borrowing, borrowing_id)
        borrowing.due_at = datetime.now(timezone.utc) - timedelta(
            days=3, seconds=1
        )
        db.commit()
    finally:
        db.close()

    # Returning the book should save its fine.
    return_response = client.put(
        f"/borrowings/{borrowing_id}/return"
    )
    assert return_response.status_code == 200

    response = client.get("/fines/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["borrowing_id"] == borrowing_id
    assert response.json()[0]["amount"] == 30.0
    assert response.json()[0]["status"] == "unpaid"

#  FINES TESTS


def test_get_fines_unpaid_only(client):
    from app.db.session import get_db
    from app.models.fine import Fine

    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    borrowing_id = borrow_response.json()["id"]

    # Create a fine directly to isolate the retrieval filter test.
    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        fine = Fine(
            borrowing_id=borrowing_id,
            amount=30,
            daily_rate=10,
            status="unpaid",
            assessed_at=datetime.now(timezone.utc),
        )
        db.add(fine)
        db.commit()
    finally:
        db.close()

    response = client.get("/fines/?unpaid_only=true")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "unpaid"



def test_pay_fine_successfully(client):
    from app.db.session import get_db
    from app.models.fine import Fine

    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201
    borrowing_id = borrow_response.json()["id"]

    # Make the borrowing overdue.
    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        borrowing = db.get(Borrowing, borrowing_id)
        borrowing.due_at = datetime.now(timezone.utc) - timedelta(
            days=3, seconds=1
        )
        db.commit()
    finally:
        db.close()

    # Returning the book creates an unpaid fine.
    return_response = client.put(
        f"/borrowings/{borrowing_id}/return"
    )
    assert return_response.status_code == 200

    fines_response = client.get("/fines/")
    fine_data = next(
        item
        for item in fines_response.json()
        if item["borrowing_id"] == borrowing_id
    )
    fine_id = fine_data["id"]

    # Mark the fine as paid.
    response = client.put(f"/fines/{fine_id}/pay")

    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    assert response.json()["paid_at"] is not None
    assert response.json()["amount"] == 30.0


def test_cannot_pay_fine_twice(client):
    from app.db.session import get_db
    from app.models.fine import Fine

    book_id = create_test_book(client)
    copy_id = create_test_copy(client, book_id)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_copy_id": copy_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201
    borrowing_id = borrow_response.json()["id"]

    db_dependency = client.app.dependency_overrides[get_db]
    db = next(db_dependency())
    try:
        borrowing = db.get(Borrowing, borrowing_id)
        borrowing.due_at = datetime.now(timezone.utc) - timedelta(
            days=3, seconds=1
        )
        db.commit()
    finally:
        db.close()

    return_response = client.put(
        f"/borrowings/{borrowing_id}/return"
    )
    assert return_response.status_code == 200

    fines_response = client.get("/fines/")
    fine_data = next(
        item
        for item in fines_response.json()
        if item["borrowing_id"] == borrowing_id
    )
    fine_id = fine_data["id"]

    first_response = client.put(f"/fines/{fine_id}/pay")
    assert first_response.status_code == 200

    second_response = client.put(f"/fines/{fine_id}/pay")
    assert second_response.status_code == 409


def test_pay_nonexistent_fine_returns_404(client):
    response = client.put("/fines/999999/pay")

    assert response.status_code == 404



def test_get_fines_pagination(client, db_session):
    # Create a book, copies, and member
    book_id = create_test_book(client)
    create_test_copy(client, book_id, barcode="FINE-PAGE-001")
    create_test_copy(client, book_id, barcode="FINE-PAGE-002")
    member_id = create_test_member(client)

    # Create two overdue borrowings and return them
    copies_response = client.get(f"/books/{book_id}/copies")
    assert copies_response.status_code == 200

    copies = copies_response.json()
    assert len(copies) == 2

    for copy in copies:
        borrow_response = client.post(
            "/borrowings/",
            json={
                "book_copy_id": copy["id"],
                "member_id": member_id,
            },
        )
        assert borrow_response.status_code == 201

        borrowing_id = borrow_response.json()["id"]

        # Simulate an overdue borrowing directly in the test database
        borrowing = db_session.get(Borrowing, borrowing_id)
        assert borrowing is not None

        borrowing.due_at = (
            datetime.now(timezone.utc) - timedelta(days=3)
        )
        db_session.commit()

        # Return the book and generate its fine
        return_response = client.put(
            f"/borrowings/{borrowing_id}/return"
        )
        assert return_response.status_code == 200

    # Request only the first fine
    response = client.get("/fines/?skip=0&limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Skip the first fine and request the second
    response = client.get("/fines/?skip=1&limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_fines_filter_by_member(client, db_session):
    # Create a book, copy, and member
    book_id = create_test_book(client)
    create_test_copy(client, book_id, barcode="FINE-MEMBER-001")
    member_id = create_test_member(client)

    # Get the book copy
    copy_response = client.get(f"/books/{book_id}/copies")
    assert copy_response.status_code == 200

    copy_id = copy_response.json()[0]["id"]

    # Borrow the book
    borrow_response = client.post(
        "/borrowings/",
        json={
            "book_copy_id": copy_id,
            "member_id": member_id,
        },
    )
    assert borrow_response.status_code == 201

    borrowing_id = borrow_response.json()["id"]

    # Simulate an overdue borrowing directly in the test database
    borrowing = db_session.get(Borrowing, borrowing_id)
    assert borrowing is not None

    borrowing.due_at = (
        datetime.now(timezone.utc) - timedelta(days=3)
    )
    db_session.commit()

    # Return the book and generate its fine
    return_response = client.put(
        f"/borrowings/{borrowing_id}/return"
    )
    assert return_response.status_code == 200

    # Filter fines by member
    response = client.get(f"/fines/?member_id={member_id}")
    assert response.status_code == 200

    fines = response.json()
    assert len(fines) == 1
    assert fines[0]["borrowing_id"] == borrowing_id


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




def test_get_fine_summary_with_paid_and_unpaid_fines(client, db_session):
    book_id = create_test_book(client)
    create_test_copy(client, book_id, barcode="SUMMARY-COPY-001")
    create_test_copy(client, book_id, barcode="SUMMARY-COPY-002")
    member_id = create_test_member(client)

    copies = client.get(f"/books/{book_id}/copies").json()
    borrowing_ids = []

    # Create two overdue borrowings and return both books
    for copy in copies:
        borrow_response = client.post(
            "/borrowings/",
            json={
                "book_copy_id": copy["id"],
                "member_id": member_id,
            },
        )
        assert borrow_response.status_code == 201

        borrowing_id = borrow_response.json()["id"]
        borrowing_ids.append(borrowing_id)

        borrowing = db_session.get(Borrowing, borrowing_id)
        assert borrowing is not None

        borrowing.due_at = (
            datetime.now(timezone.utc) - timedelta(days=3)
        )
        db_session.commit()

        return_response = client.put(
            f"/borrowings/{borrowing_id}/return"
        )
        assert return_response.status_code == 200

    # Retrieve the generated fines
    fines_response = client.get("/fines/")
    assert fines_response.status_code == 200

    fines = fines_response.json()
    assert len(fines) == 2

    # Pay the first fine
    fine_id = fines[0]["id"]
    payment_response = client.put(f"/fines/{fine_id}/pay")
    assert payment_response.status_code == 200

    # Check the summary
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



def test_member_borrowing_history_returns_records(client):
    book_id = create_test_book(client)
    create_test_copy(client, book_id, barcode="HISTORY-COPY-001")
    member_id = create_test_member(client)

    copies = client.get(f"/books/{book_id}/copies").json()
    copy_id = copies[0]["id"]

    borrow_response = client.post(
        "/borrowings/",
        json={
            "book_copy_id": copy_id,
            "member_id": member_id,
        },
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
