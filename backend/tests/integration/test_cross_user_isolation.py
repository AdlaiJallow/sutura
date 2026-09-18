"""Cross-user isolation (D-020, spec §34): a user must never be able to reach another user's
records by changing an ID. A financial period that exists but belongs to another user must be
indistinguishable from a genuinely missing one — 404, never 403, never the record's data."""
from fastapi.testclient import TestClient


def test_user_cannot_fetch_another_users_financial_period_by_id(
    client: TestClient, auth_headers_factory
):
    user_a_headers = auth_headers_factory("alice")
    user_b_headers = auth_headers_factory("bob")

    create_resp = client.post(
        "/api/v1/financial-periods", json={"year": 2025, "month": 8}, headers=user_a_headers
    )
    assert create_resp.status_code == 201, create_resp.text
    period_id = create_resp.json()["id"]

    # Owner can fetch it.
    own_resp = client.get(f"/api/v1/financial-periods/{period_id}", headers=user_a_headers)
    assert own_resp.status_code == 200

    # A different authenticated user requesting the exact same id gets 404, not 403, and never
    # sees user A's data.
    cross_resp = client.get(f"/api/v1/financial-periods/{period_id}", headers=user_b_headers)
    assert cross_resp.status_code == 404
    assert "year" not in cross_resp.json()

    # Same rule for mutating actions: user B cannot close user A's period.
    close_resp = client.post(f"/api/v1/financial-periods/{period_id}/close", headers=user_b_headers)
    assert close_resp.status_code == 404

    # And user B cannot reopen a period they can't even see.
    reopen_resp = client.post(
        f"/api/v1/financial-periods/{period_id}/reopen",
        json={"reason": "trying to tamper"},
        headers=user_b_headers,
    )
    assert reopen_resp.status_code == 404

    # Listing periods never leaks across users.
    list_resp = client.get("/api/v1/financial-periods", headers=user_b_headers)
    assert list_resp.status_code == 200
    ids = [row["id"] for row in list_resp.json()["data"]]
    assert period_id not in ids
