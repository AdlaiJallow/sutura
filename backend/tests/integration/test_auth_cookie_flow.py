"""D-026: refresh token is delivered via an httpOnly cookie, never a JSON body field, and is
rotated on every use. Covers login/refresh/logout's cookie behavior end to end."""
import uuid

from fastapi.testclient import TestClient

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _register(client: TestClient, email: str, password: str = "correct-horse-1") -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Cookie Tester"},
    )
    assert resp.status_code == 201, resp.text


def _unique_email(prefix: str = "cookie") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


def test_login_sets_httponly_refresh_cookie_and_body_has_no_refresh_token(client: TestClient):
    email = _unique_email()
    password = "correct-horse-1"
    _register(client, email, password)

    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" not in body

    assert REFRESH_COOKIE_NAME in resp.cookies
    set_cookie_header = resp.headers.get("set-cookie", "")
    assert "httponly" in set_cookie_header.lower()
    assert f"path={REFRESH_COOKIE_PATH}".lower() in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()


def test_refresh_reads_cookie_and_returns_new_access_token(client: TestClient):
    email = _unique_email()
    password = "correct-horse-1"
    _register(client, email, password)

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    old_access_token = login_resp.json()["access_token"]

    # TestClient automatically stores and resends cookies via its internal cookie jar.
    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200, refresh_resp.text
    new_body = refresh_resp.json()
    assert "access_token" in new_body
    assert "refresh_token" not in new_body
    assert new_body["access_token"] != old_access_token


def test_refresh_rotates_the_cookie_and_old_refresh_token_is_revoked(client: TestClient):
    email = _unique_email()
    password = "correct-horse-1"
    _register(client, email, password)

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    old_refresh_value = login_resp.cookies.get(REFRESH_COOKIE_NAME)
    assert old_refresh_value is not None

    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200, refresh_resp.text
    new_refresh_value = client.cookies.get(REFRESH_COOKIE_NAME)
    assert new_refresh_value is not None
    assert new_refresh_value != old_refresh_value

    # Reusing the OLD (now-revoked) refresh token must fail, even though it hasn't expired.
    client.cookies.set(REFRESH_COOKIE_NAME, old_refresh_value)
    reuse_resp = client.post("/api/v1/auth/refresh")
    assert reuse_resp.status_code == 401, reuse_resp.text


def test_refresh_with_no_cookie_returns_401(client: TestClient):
    resp = client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_logout_revokes_refresh_token_and_clears_cookie(client: TestClient):
    email = _unique_email()
    password = "correct-horse-1"
    _register(client, email, password)

    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text

    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 204, logout_resp.text

    # The cookie must be cleared client-side...
    set_cookie_header = logout_resp.headers.get("set-cookie", "")
    assert REFRESH_COOKIE_NAME in set_cookie_header

    # ...and the revoked token must no longer work even if resent manually.
    refresh_token_value = login_resp.cookies.get(REFRESH_COOKIE_NAME)
    client.cookies.set(REFRESH_COOKIE_NAME, refresh_token_value)
    reuse_resp = client.post("/api/v1/auth/refresh")
    assert reuse_resp.status_code == 401, reuse_resp.text


def test_refresh_rejects_a_deactivated_account(client: TestClient):
    """Found in Phase 5 review: refresh never checked is_active, so a refresh token minted
    before DELETE /users/me could keep issuing fresh access tokens for a deactivated account
    indefinitely. Fixed to revoke the token and reject outright, same as an expired/invalid one."""
    email = _unique_email()
    password = "correct-horse-1"
    _register(client, email, password)
    login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    access_token = login_resp.json()["access_token"]

    delete_resp = client.request(
        "DELETE",
        "/api/v1/users/me",
        json={"password": password},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert delete_resp.status_code == 204, delete_resp.text

    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 401, refresh_resp.text

    # The refresh token is now revoked outright, not just refused once.
    refresh_again_resp = client.post("/api/v1/auth/refresh")
    assert refresh_again_resp.status_code == 401, refresh_again_resp.text


def test_logout_with_no_cookie_is_a_no_op_not_an_error(client: TestClient):
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 204, resp.text
