
import pytest


@pytest.fixture()
def client(authenticated_client):
    return authenticated_client


def test_create_book(client):
    response = client.post(
        "/books/",
        json={
            "title": "Python Fundamentals",
            "isbn": "TEST-ISBN-001",
            "description": "A book for testing",
            "published_year": 2025,
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["title"] == "Python Fundamentals"
    assert data["isbn"] == "TEST-ISBN-001"
    assert data["description"] == "A book for testing"
    assert data["published_year"] == 2025
    assert data["id"] is not None


def test_duplicate_isbn_returns_conflict(client):
    book_data = {
        "title": "Python Fundamentals",
        "isbn": "TEST-ISBN-002",
    }

    first_response = client.post("/books/", json=book_data)
    second_response = client.post("/books/", json=book_data)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_missing_book_returns_404(client):
    response = client.get("/books/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "   "),
        ("isbn", "   "),
    ],
)
def test_book_rejects_whitespace_only_required_fields(
    client, field, value
):
    response = client.post(
        "/books/",
        json={
            "title": "Valid Book Title",
            "isbn": "VALID-ISBN-001",
            field: value,
        },
    )

    assert response.status_code == 422


def test_book_title_and_isbn_are_trimmed(client):
    response = client.post(
        "/books/",
        json={
            "title": "  Python Fundamentals  ",
            "isbn": "  TRIM-ISBN-001  ",
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Python Fundamentals"
    assert response.json()["isbn"] == "TRIM-ISBN-001"


def test_create_book_trims_description(client):
    response = client.post(
        "/books/",
        json={
            "title": "Description Test",
            "isbn": "DESC-TEST-001",
            "description": "  A useful book  ",
        },
    )

    assert response.status_code == 201
    assert response.json()["description"] == "A useful book"


def test_create_book_whitespace_description_becomes_none(client):
    response = client.post(
        "/books/",
        json={
            "title": "Empty Description Test",
            "isbn": "DESC-TEST-002",
            "description": "   ",
        },
    )

    assert response.status_code == 201
    assert response.json()["description"] is None


def test_update_book_whitespace_description_becomes_none(client):
    create_response = client.post(
        "/books/",
        json={
            "title": "Description Update Test",
            "isbn": "DESC-TEST-003",
            "description": "Existing description",
        },
    )

    assert create_response.status_code == 201
    book_id = create_response.json()["id"]

    response = client.put(
        f"/books/{book_id}",
        json={"description": "   "},
    )

    assert response.status_code == 200
    assert response.json()["description"] is None

def test_create_book_rejects_future_publication_year(client):
    from datetime import datetime, timezone

    future_year = datetime.now(timezone.utc).year + 1

    response = client.post(
        "/books/",
        json={
            "title": "Future Publication",
            "isbn": "FUTURE-ISBN-001",
            "published_year": future_year,
        },
    )

    assert response.status_code == 422

def test_create_book_without_publication_year(client):
    response = client.post(
        "/books/",
        json={
            "title": "Unknown Publication Year",
            "isbn": "UNKNOWN-YEAR-001",
            "published_year": None,
        },
    )

    assert response.status_code == 201
    assert response.json()["published_year"] is None


def test_update_book_changes_only_provided_fields(client):
    create_response = client.post(
        "/books/",
        json={
            "title": "Original Title",
            "isbn": "UPDATE-BOOK-001",
            "description": "Original description",
            "published_year": 2020,
        },
    )

    assert create_response.status_code == 201
    book_id = create_response.json()["id"]

    response = client.put(
        f"/books/{book_id}",
        json={"description": "Updated description"},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["title"] == "Original Title"
    assert data["isbn"] == "UPDATE-BOOK-001"
    assert data["description"] == "Updated description"
    assert data["published_year"] == 2020


def test_update_book_rejects_empty_payload(client):
    create_response = client.post(
        "/books/",
        json={
            "title": "Empty Update Test",
            "isbn": "UPDATE-BOOK-002",
        },
    )

    assert create_response.status_code == 201
    book_id = create_response.json()["id"]

    response = client.put(f"/books/{book_id}", json={})

    assert response.status_code == 422
    assert response.json()["detail"] == "Provide at least one field to update"


@pytest.mark.parametrize("field", ["title", "isbn"])
def test_update_book_rejects_null_required_fields(client, field):
    create_response = client.post(
        "/books/",
        json={
            "title": "Null Update Test",
            "isbn": "UPDATE-BOOK-003",
        },
    )

    assert create_response.status_code == 201
    book_id = create_response.json()["id"]

    response = client.put(
        f"/books/{book_id}",
        json={field: None},
    )

    assert response.status_code == 422


def test_update_book_rejects_duplicate_isbn(client):
    first_response = client.post(
        "/books/",
        json={
            "title": "First Book",
            "isbn": "UPDATE-BOOK-004",
        },
    )
    second_response = client.post(
        "/books/",
        json={
            "title": "Second Book",
            "isbn": "UPDATE-BOOK-005",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    second_book_id = second_response.json()["id"]

    response = client.put(
        f"/books/{second_book_id}",
        json={"isbn": "UPDATE-BOOK-004"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A book with this ISBN already exists"
    )
