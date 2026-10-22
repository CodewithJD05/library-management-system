
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
