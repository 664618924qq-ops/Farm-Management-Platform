def test_login_returns_token_and_user(client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["token"] == "demo-token-admin"
    assert data["user"]["role"] == "admin"


def test_login_rejects_invalid_credentials(client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"
