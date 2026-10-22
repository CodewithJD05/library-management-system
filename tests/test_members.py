
def test_create_member(client):
    response = client.post(
        "/members/",
        json={
            "full_name": "Jay Jadav",
            "email": "jay.test@example.com",
            "phone": "9876543210",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["full_name"] == "Jay Jadav"
    assert data["email"] == "jay.test@example.com"
    assert data["is_active"] is True
    assert data["id"] is not None


def test_duplicate_email_returns_conflict(client):
    member_data = {
        "full_name": "Jay Jadav",
        "email": "duplicate@example.com",
    }

    first_response = client.post("/members/", json=member_data)
    second_response = client.post("/members/", json=member_data)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_invalid_email_returns_validation_error(client):
    response = client.post(
        "/members/",
        json={
            "full_name": "Test Member",
            "email": "not-an-email",
        },
    )

    assert response.status_code == 422


def test_missing_member_returns_404(client):
    response = client.get("/members/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Member not found"
