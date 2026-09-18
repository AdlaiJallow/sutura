"""Integration test: register -> login -> create financial period -> close -> reopen (with
reason). Exercises the real DB, real service layer, real audit trail — not mocks."""
from decimal import Decimal

from fastapi.testclient import TestClient


def test_register_login_create_close_reopen_period(client: TestClient, auth_headers: dict[str, str]):
    # Create a financial period for a month unlikely to already exist for a fresh user.
    create_resp = client.post(
        "/api/v1/financial-periods", json={"year": 2025, "month": 6}, headers=auth_headers
    )
    assert create_resp.status_code == 201, create_resp.text
    period = create_resp.json()
    assert period["status"] == "OPEN"
    assert period["reopened_count"] == 0
    period_id = period["id"]

    # Fetch it back by id.
    get_resp = client.get(f"/api/v1/financial-periods/{period_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == period_id

    # Close it.
    close_resp = client.post(f"/api/v1/financial-periods/{period_id}/close", headers=auth_headers)
    assert close_resp.status_code == 200, close_resp.text
    closed = close_resp.json()
    assert closed["status"] == "CLOSED"
    assert closed["closed_at"] is not None

    # A summary should now exist for the closed period.
    summary_resp = client.get(f"/api/v1/financial-periods/{period_id}/summary", headers=auth_headers)
    assert summary_resp.status_code == 200, summary_resp.text
    summary = summary_resp.json()
    assert summary["triggered_by"] == "CLOSE"
    assert Decimal(str(summary["total_monthly_income"])) == Decimal("0.0000")

    # Closing an already-closed period is rejected (409).
    reclose_resp = client.post(f"/api/v1/financial-periods/{period_id}/close", headers=auth_headers)
    assert reclose_resp.status_code == 409

    # Reopening without a reason is rejected.
    bad_reopen = client.post(
        f"/api/v1/financial-periods/{period_id}/reopen", json={"reason": ""}, headers=auth_headers
    )
    assert bad_reopen.status_code == 422

    # Reopen with a reason succeeds and is audited (reopened_count increments, status flips back).
    reopen_resp = client.post(
        f"/api/v1/financial-periods/{period_id}/reopen",
        json={"reason": "Forgot to record June rent."},
        headers=auth_headers,
    )
    assert reopen_resp.status_code == 200, reopen_resp.text
    reopened = reopen_resp.json()
    assert reopened["status"] == "OPEN"
    assert reopened["reopened_count"] == 1
    assert reopened["closed_at"] is None

    # Reopening an already-open period is rejected.
    bad_reopen_again = client.post(
        f"/api/v1/financial-periods/{period_id}/reopen",
        json={"reason": "Trying again."},
        headers=auth_headers,
    )
    assert bad_reopen_again.status_code == 409


def test_cannot_create_duplicate_period_for_same_month(client: TestClient, auth_headers: dict[str, str]):
    resp1 = client.post("/api/v1/financial-periods", json={"year": 2025, "month": 7}, headers=auth_headers)
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/financial-periods", json={"year": 2025, "month": 7}, headers=auth_headers)
    assert resp2.status_code == 409


def test_unauthenticated_request_is_rejected(client: TestClient):
    resp = client.get("/api/v1/financial-periods")
    assert resp.status_code == 401
