
def test_dashboard_summary_with_empty_database(authenticated_client):
    client = authenticated_client
    response = client.get("/dashboard/summary")

    assert response.status_code == 200

    assert response.json() == {
        "total_books": 0,
        "total_copies": 0,
        "available_copies": 0,
        "borrowed_copies": 0,
        "active_members": 0,
        "active_loans": 0,
        "overdue_loans": 0,
    }


def test_dashboard_summary_counts_books_and_members(authenticated_client):
    client = authenticated_client
    from tests.test_borrowings import (
        create_test_book,
        create_test_member,
        create_test_copy,
    )

    book_id = create_test_book(client)
    create_test_copy(
        client,
        book_id,
        barcode="DASHBOARD-COPY-001",
    )
    create_test_member(client)

    response = client.get("/dashboard/summary")

    assert response.status_code == 200

    data = response.json()

    assert data["total_books"] == 1
    assert data["total_copies"] == 1
    assert data["available_copies"] == 1
    assert data["borrowed_copies"] == 0
    assert data["active_members"] == 1
    assert data["active_loans"] == 0
    assert data["overdue_loans"] == 0



def test_dashboard_updates_after_borrow_and_return(authenticated_client):
    client = authenticated_client
    from tests.test_borrowings import (
        create_test_book,
        create_test_member,
        create_test_copy,
    )

    book_id = create_test_book(client)
    member_id = create_test_member(client)

    create_test_copy(
        client,
        book_id,
        barcode="DASHBOARD-FLOW-001",
    )

    copies = client.get(f"/books/{book_id}/copies").json()
    copy_id = copies[0]["id"]

    # Before borrowing
    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    assert response.json()["available_copies"] == 1
    assert response.json()["active_loans"] == 0

    # Borrow the copy
    borrow_response = client.post(
        "/borrowings/",
        json={
            "book_copy_id": copy_id,
            "member_id": member_id,
        },
    )
    assert borrow_response.status_code == 201
    borrowing_id = borrow_response.json()["id"]

    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    assert response.json()["available_copies"] == 0
    assert response.json()["borrowed_copies"] == 1
    assert response.json()["active_loans"] == 1

    # Return the copy
    return_response = client.put(
        f"/borrowings/{borrowing_id}/return"
    )
    assert return_response.status_code == 200

    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    assert response.json()["available_copies"] == 1
    assert response.json()["borrowed_copies"] == 0
    assert response.json()["active_loans"] == 0



def test_dashboard_requires_authentication(client):
    response = client.get("/dashboard/summary")

    assert response.status_code == 401