"""PATCH (update) endpoints added in Phase 3 for Salary/Allowance/Income/Expense/SavingsItem.

Covers, for every one of the five record types:
- a happy-path partial update,
- optimistic-locking conflict on a stale `expected_updated_at` (D-018, spec §38-30) — the
  second write using the same (now stale) token must be rejected with 409 and must NOT apply,
- rejection with 409 once the owning financial period is CLOSED (spec §37/§38).
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


def _create_period(client: TestClient, headers: dict, year: int, month: int) -> str:
    resp = client.post(
        "/api/v1/financial-periods", json={"year": year, "month": month}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


RESOURCES = [
    pytest.param(
        "salaries",
        lambda pid: {"financial_period_id": pid, "net_amount": "1000.00", "currency": "GMD"},
        {"net_amount": "1200.00"},
        "net_amount",
        id="salary",
    ),
    pytest.param(
        "allowances",
        lambda pid: {
            "financial_period_id": pid,
            "name": "Housing",
            "amount": "300.00",
            "currency": "GMD",
            "date_received": "2030-01-15",
        },
        {"amount": "350.00"},
        "amount",
        id="allowance",
    ),
    pytest.param(
        "income",
        lambda pid: {
            "financial_period_id": pid,
            "income_type": "FREELANCE",
            "description": "Side gig",
            "amount": "150.00",
            "currency": "GMD",
            "date_received": "2030-01-15",
        },
        {"amount": "175.00"},
        "amount",
        id="income",
    ),
    pytest.param(
        "expenses",
        lambda pid: {
            "financial_period_id": pid,
            "name": "Groceries",
            "expense_category": "FOOD",
            "amount": "50.00",
            "currency": "GMD",
            "expense_date": "2030-01-15",
        },
        {"amount": "60.00"},
        "amount",
        id="expense",
    ),
    pytest.param(
        "savings-items",
        lambda pid: {
            "financial_period_id": pid,
            "name": "Emergency fund",
            "amount": "100.00",
            "currency": "GMD",
            "date": "2030-01-15",
        },
        {"amount": "120.00"},
        "amount",
        id="savings-item",
    ),
]


@pytest.mark.parametrize("resource, build_payload, update_payload, amount_field", RESOURCES)
def test_update_optimistic_lock_and_closed_period(
    client: TestClient,
    auth_headers: dict,
    resource: str,
    build_payload,
    update_payload: dict,
    amount_field: str,
):
    period_id = _create_period(client, auth_headers, 2030, 1)

    create_resp = client.post(
        f"/api/v1/{resource}", json=build_payload(period_id), headers=auth_headers
    )
    assert create_resp.status_code == 201, create_resp.text
    record = create_resp.json()
    assert "updated_at" in record
    original_updated_at = record["updated_at"]

    # Happy-path update using the updated_at the client last read.
    body = dict(update_payload)
    body["expected_updated_at"] = original_updated_at
    update_resp = client.patch(
        f"/api/v1/{resource}/{record['id']}", json=body, headers=auth_headers
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert Decimal(str(updated[amount_field])) == Decimal(update_payload[amount_field]).quantize(
        Decimal("0.0001")
    )
    new_updated_at = updated["updated_at"]
    assert new_updated_at != original_updated_at

    # Re-using the now-stale updated_at is rejected (409) and must not apply.
    stale_retry = client.patch(
        f"/api/v1/{resource}/{record['id']}", json=body, headers=auth_headers
    )
    assert stale_retry.status_code == 409, stale_retry.text

    get_resp = client.get(f"/api/v1/{resource}/{record['id']}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert Decimal(str(get_resp.json()[amount_field])) == Decimal(
        update_payload[amount_field]
    ).quantize(Decimal("0.0001"))
    assert get_resp.json()["updated_at"] == new_updated_at

    # Closing the period blocks any further update, even with a fresh updated_at.
    close_resp = client.post(f"/api/v1/financial-periods/{period_id}/close", headers=auth_headers)
    assert close_resp.status_code == 200, close_resp.text

    body2 = dict(update_payload)
    body2["expected_updated_at"] = new_updated_at
    closed_resp = client.patch(
        f"/api/v1/{resource}/{record['id']}", json=body2, headers=auth_headers
    )
    assert closed_resp.status_code == 409, closed_resp.text


def test_update_rejects_empty_body(client: TestClient, auth_headers: dict):
    """Sending nothing but the lock token is a no-op request and is rejected rather than
    silently succeeding with no change."""
    period_id = _create_period(client, auth_headers, 2030, 2)
    create_resp = client.post(
        "/api/v1/salaries",
        json={"financial_period_id": period_id, "net_amount": "500.00", "currency": "GMD"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    salary = create_resp.json()

    resp = client.patch(
        f"/api/v1/salaries/{salary['id']}",
        json={"expected_updated_at": salary["updated_at"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


def test_cross_user_cannot_update_another_users_salary(
    client: TestClient, auth_headers_factory
):
    """Representative case for D-020 applied to the new update endpoints: identical ownership
    scoping applies uniformly to allowances/income/expenses/savings-items too (same
    `get_owned` + `update_owned(..., user_id=...)` pattern in every module's repository)."""
    alice = auth_headers_factory("alice")
    bob = auth_headers_factory("bob")

    period_id = _create_period(client, alice, 2030, 3)
    create_resp = client.post(
        "/api/v1/salaries",
        json={"financial_period_id": period_id, "net_amount": "800.00", "currency": "GMD"},
        headers=alice,
    )
    assert create_resp.status_code == 201, create_resp.text
    salary = create_resp.json()

    resp = client.patch(
        f"/api/v1/salaries/{salary['id']}",
        json={"net_amount": "1.00", "expected_updated_at": salary["updated_at"]},
        headers=bob,
    )
    assert resp.status_code == 404, resp.text

    # And it truly never applied.
    get_resp = client.get(f"/api/v1/salaries/{salary['id']}", headers=alice)
    assert Decimal(str(get_resp.json()["net_amount"])) == Decimal("800.0000")
