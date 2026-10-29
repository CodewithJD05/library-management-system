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


def test_update_member_rejects_duplicate_email(client):
    first = client.post(
        "/members/",
        json={
            "full_name": "First Member",
            "email": "first@example.com",
        },
    )
    second = client.post(
        "/members/",
        json={
            "full_name": "Second Member",
            "email": "second@example.com",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201

    second_id = second.json()["id"]

    response = client.put(
        f"/members/{second_id}",
        json={"email": "first@example.com"},
    )

    assert response.status_code == 409

    unchanged = client.get(f"/members/{second_id}")
    assert unchanged.status_code == 200
    assert unchanged.json()["email"] == "second@example.com"


def test_update_member_rejects_empty_update(client):
    created = client.post(
        "/members/",
        json={
            "full_name": "Test Member",
            "email": "empty.update@example.com",
        },
    )
    member_id = created.json()["id"]

    response = client.put(f"/members/{member_id}", json={})

    assert response.status_code == 422
    assert response.json()["detail"] == "No fields provided for update"


def test_search_members_by_name(client):
    client.post(
        "/members/",
        json={
            "full_name": "Alice Johnson",
            "email": "alice.search@example.com",
        },
    )
    client.post(
        "/members/",
        json={
            "full_name": "Bob Smith",
            "email": "bob.search@example.com",
        },
    )

    response = client.get("/members/", params={"search": "alice"})

    assert response.status_code == 200
    assert any(
        member["full_name"] == "Alice Johnson"
        for member in response.json()
    )
    assert all(
        "alice" in member["full_name"].lower()
        for member in response.json()
    )


def test_search_members_by_id(client):
    created = client.post(
        "/members/",
        json={
            "full_name": "ID Search Member",
            "email": "id.search@example.com",
        },
    )
    member_id = created.json()["id"]

    response = client.get(
        "/members/",
        params={"search": str(member_id)},
    )

    assert response.status_code == 200
    assert [member["id"] for member in response.json()] == [member_id]


def test_list_members_supports_pagination(client):
    for number in range(3):
        response = client.post(
            "/members/",
            json={
                "full_name": f"Pagination Member {number}",
                "email": f"pagination{number}@example.com",
            },
        )
        assert response.status_code == 201

    first_page = client.get(
        "/members/",
        params={"skip": 0, "limit": 2},
    )
    second_page = client.get(
        "/members/",
        params={"skip": 2, "limit": 2},
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 1

    first_ids = {member["id"] for member in first_page.json()}
    second_ids = {member["id"] for member in second_page.json()}
    assert first_ids.isdisjoint(second_ids)
