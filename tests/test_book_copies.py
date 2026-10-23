
def create_test_book(client):
    response = client.post(
        "/books/",
        json={
            "title": "Book Copy Testing",
            "isbn": "COPY-TEST-ISBN-001",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_book_copy(client):
    book_id = create_test_book(client)

    response = client.post(
        f"/books/{book_id}/copies",
        json={"barcode": "COPY-TEST-001"},
    )

    assert response.status_code == 201
    data = response.json()

    assert data["book_id"] == book_id
    assert data["barcode"] == "COPY-TEST-001"
    assert data["status"] == "available"
    assert "id" in data


def test_list_book_copies(client):
    book_id = create_test_book(client)

    client.post(
        f"/books/{book_id}/copies",
        json={"barcode": "COPY-LIST-001"},
    )
    client.post(
        f"/books/{book_id}/copies",
        json={"barcode": "COPY-LIST-002"},
    )

    response = client.get(f"/books/{book_id}/copies")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert all(copy["book_id"] == book_id for copy in response.json())


def test_create_copy_for_nonexistent_book_returns_404(client):
    response = client.post(
        "/books/999999/copies",
        json={"barcode": "COPY-MISSING-001"},
    )

    assert response.status_code == 404


def test_list_copies_for_nonexistent_book_returns_404(client):
    response = client.get("/books/999999/copies")

    assert response.status_code == 404


def test_duplicate_barcode_is_rejected(client):
    book_id = create_test_book(client)

    first_response = client.post(
        f"/books/{book_id}/copies",
        json={"barcode": "COPY-DUPLICATE-001"},
    )
    assert first_response.status_code == 201

    second_response = client.post(
        f"/books/{book_id}/copies",
        json={"barcode": "COPY-DUPLICATE-001"},
    )

    assert second_response.status_code == 409


def test_copy_barcode_is_required(client):
    book_id = create_test_book(client)

    response = client.post(
        f"/books/{book_id}/copies",
        json={},
    )

    assert response.status_code == 422
