import pytest


@pytest.fixture()
def client(authenticated_client):
    return authenticated_client


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



def test_deactivate_member(client):
    member_response = client.post(
        "/members/",
        json={
            "full_name": "Test Member",
            "email": "deactivate@example.com",
        },
    )
    member_id = member_response.json()["id"]

    response = client.patch(
        f"/members/{member_id}/status",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_reactivate_member(client):
    member_response = client.post(
        "/members/",
        json={
            "full_name": "Test Member",
            "email": "reactivate@example.com",
        },
    )
    member_id = member_response.json()["id"]

    client.patch(
        f"/members/{member_id}/status",
        json={"is_active": False},
    )

    response = client.patch(
        f"/members/{member_id}/status",
        json={"is_active": True},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_update_status_for_missing_member_returns_404(client):
    response = client.patch(
        "/members/99999/status",
        json={"is_active": False},
    )

    assert response.status_code == 404


def test_create_member_trims_name(client):
    response = client.post(
        "/members/",
        json={
            "full_name": "  Jay Jadav  ",
            "email": "trimmed.name@example.com",
        },
    )

    assert response.status_code == 201
    assert response.json()["full_name"] == "Jay Jadav"


def test_update_member_rejects_whitespace_only_name(client):
    create_response = client.post(
        "/members/",
        json={
            "full_name": "Jay Jadav",
            "email": "update.name@example.com",
        },
    )
    member_id = create_response.json()["id"]

    response = client.put(
        f"/members/{member_id}",
        json={"full_name": "   "},
    )

    assert response.status_code == 422