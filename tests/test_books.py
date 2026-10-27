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
    assert "id" in data


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