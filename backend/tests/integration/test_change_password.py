"""Found in Phase 5 review: `ChangePasswordRequest.new_password` had no length constraint,
unlike `RegisterRequest.password` / `ResetPasswordRequest.new_password` (both `min_length=8`).
Fixed to match; this covers both the length rejection and the existing happy-path/wrong-password
behavior the frontend already relies on."""
import uuid

from fastapi.testclient import TestClient


def _unique_email(prefix: str = "changepw") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


def _register_and_login(client: TestClient, email: str, password: str) -> str:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Change Password Tester"},
    )
    assert resp.status_code == 201, resp.text
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    return login_resp.json()["access_token"]


def test_new_password_too_short_is_rejected_with_422(client: TestClient):
    email = _unique_email()
    password = "correct-horse-1"
    access_token = _register_and_login(client, email, password)

    resp = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": password, "new_password": "short"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_change_password_happy_path_and_wrong_current_password(client: TestClient):
    email = _unique_email()
    password = "correct-horse-1"
    access_token = _register_and_login(client, email, password)

    wrong_resp = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "not-the-password", "new_password": "brand-new-password-1"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert wrong_resp.status_code == 401, wrong_resp.text

    ok_resp = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": password, "new_password": "brand-new-password-1"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert ok_resp.status_code == 204, ok_resp.text

    old_login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert old_login.status_code == 401, old_login.text

    new_login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "brand-new-password-1"}
    )
    assert new_login.status_code == 200, new_login.text
