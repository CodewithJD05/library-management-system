
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
    member_id = create_test_member(client)

    # First borrowing should succeed
    response = client.post(
        "/borrowings/",
        json={"book_id": book_id, "member_id": member_id},
    )
    assert response.status_code == 201
    borrowing_id = response.json()["id"]
    assert response.json()["returned_at"] is None

    # The same book cannot be borrowed while still out
    duplicate_response = client.post(
        "/borrowings/",
        json={"book_id": book_id, "member_id": member_id},
    )
    assert duplicate_response.status_code == 409

    # Return the book
    return_response = client.put(
        f"/borrowings/{borrowing_id}/return"
    )
    assert return_response.status_code == 200
    assert return_response.json()["returned_at"] is not None

    # The same book can be borrowed again after return
    second_borrow_response = client.post(
        "/borrowings/",
        json={"book_id": book_id, "member_id": member_id},
    )
    assert second_borrow_response.status_code == 201


def test_borrowing_nonexistent_book_returns_404(client):
    member_id = create_test_member(client)

    response = client.post(
        "/borrowings/",
        json={"book_id": 999999, "member_id": member_id},
    )

    assert response.status_code == 404


def test_borrowing_inactive_member_is_rejected(client):
    book_id = create_test_book(client)
    member_id = create_test_member(client)

    # Deactivate the member through the existing Member API
    update_response = client.put(
        f"/members/{member_id}",
        json={"is_active": False},
    )
    assert update_response.status_code == 200

    response = client.post(
        "/borrowings/",
        json={"book_id": book_id, "member_id": member_id},
    )

    assert response.status_code == 400

def test_cannot_delete_book_with_borrowing_history(client):
    book_id = create_test_book(client)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_id": book_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    delete_response = client.delete(f"/books/{book_id}")

    assert delete_response.status_code == 409


def test_cannot_delete_member_with_borrowing_history(client):
    book_id = create_test_book(client)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_id": book_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    delete_response = client.delete(f"/members/{member_id}")

    assert delete_response.status_code == 409

def test_filter_active_borrowings(client):
    book_id = create_test_book(client)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_id": book_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    response = client.get("/borrowings/?active_only=true")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["returned_at"] is None

def test_filter_borrowings_by_member(client):
    book_id = create_test_book(client)
    member_id = create_test_member(client)

    borrow_response = client.post(
        "/borrowings/",
        json={"book_id": book_id, "member_id": member_id},
    )
    assert borrow_response.status_code == 201

    response = client.get(
        f"/borrowings/?member_id={member_id}"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["member_id"] == member_id