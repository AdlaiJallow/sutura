"""Phase 4 (Accounts) coverage for `app.banks` / `app.transactions`:

- BankAccount PATCH (update): happy path + optimistic-locking conflict (D-018).
- POST /bank-transactions/transfer: moves money between two of the same user's accounts
  atomically, both balances updated, `transfer_pair_id` links the two legs (spec §18, D-011).
- Transfer rejected: same-account, either account not owned by the requesting user (D-020,
  404 not 403), either account inactive.
- Bank transaction creation is rejected once the owning financial period is CLOSED (the gap
  fixed in this phase — every other module already enforces this).
"""
from decimal import Decimal

from fastapi.testclient import TestClient


def _create_period(client: TestClient, headers: dict, year: int, month: int) -> str:
    resp = client.post(
        "/api/v1/financial-periods", json={"year": year, "month": month}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_account(
    client: TestClient, headers: dict, name: str, opening_balance: str = "0"
) -> dict:
    resp = client.post(
        "/api/v1/bank-accounts",
        json={
            "account_name": name,
            "institution_name": "Trust Bank",
            "account_type": "BANK",
            "account_identifier": "1234567890",
            "currency": "GMD",
            "opening_balance": opening_balance,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_masks_identifier_and_get_roundtrips(client: TestClient, auth_headers: dict):
    account = _create_account(client, auth_headers, "Main Checking")
    assert account["account_identifier_last4"] == "7890"
    assert "account_identifier" not in account
    assert Decimal(str(account["current_balance"])) == Decimal("0.0000")


def test_create_rejects_invalid_account_type_with_clean_422(
    client: TestClient, auth_headers: dict
):
    """Found during Phase 5 frontend verification: `account_type` had no Pydantic-level
    validation, only the DB CHECK constraint — an invalid value raised a raw IntegrityError/500
    instead of the app's error envelope. Fixed to mirror the income_type/expense_category/
    payment_method pattern; this is the regression test."""
    resp = client.post(
        "/api/v1/bank-accounts",
        json={"account_name": "Bad Type Account", "account_type": "BOGUS_TYPE"},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_bank_account_happy_path_optimistic_lock_and_reactivation(
    client: TestClient, auth_headers: dict
):
    account = _create_account(client, auth_headers, "Savings Account")
    original_updated_at = account["updated_at"]

    update_resp = client.patch(
        f"/api/v1/bank-accounts/{account['id']}",
        json={
            "account_name": "Savings Account (renamed)",
            "notes": "Primary savings",
            "account_identifier": "9999888877",
            "expected_updated_at": original_updated_at,
        },
        headers=auth_headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["account_name"] == "Savings Account (renamed)"
    assert updated["notes"] == "Primary savings"
    assert updated["account_identifier_last4"] == "8877"
    new_updated_at = updated["updated_at"]
    assert new_updated_at != original_updated_at

    # Re-using the now-stale updated_at is rejected (409) and does not apply.
    stale_retry = client.patch(
        f"/api/v1/bank-accounts/{account['id']}",
        json={"account_name": "Should not apply", "expected_updated_at": original_updated_at},
        headers=auth_headers,
    )
    assert stale_retry.status_code == 409, stale_retry.text

    # Deactivate, then reactivate via the update endpoint (is_active: true).
    deactivate_resp = client.delete(
        f"/api/v1/bank-accounts/{account['id']}", headers=auth_headers
    )
    assert deactivate_resp.status_code == 204

    inactive = client.get(f"/api/v1/bank-accounts/{account['id']}", headers=auth_headers).json()
    assert inactive["is_active"] is False

    reactivate_resp = client.patch(
        f"/api/v1/bank-accounts/{account['id']}",
        json={"is_active": True, "expected_updated_at": inactive["updated_at"]},
        headers=auth_headers,
    )
    assert reactivate_resp.status_code == 200, reactivate_resp.text
    assert reactivate_resp.json()["is_active"] is True


def test_update_rejects_empty_body(client: TestClient, auth_headers: dict):
    account = _create_account(client, auth_headers, "Empty Update Account")
    resp = client.patch(
        f"/api/v1/bank-accounts/{account['id']}",
        json={"expected_updated_at": account["updated_at"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


def test_cross_user_cannot_update_another_users_bank_account(
    client: TestClient, auth_headers_factory
):
    alice = auth_headers_factory("alice")
    bob = auth_headers_factory("bob")
    account = _create_account(client, alice, "Alice's Account")

    resp = client.patch(
        f"/api/v1/bank-accounts/{account['id']}",
        json={"account_name": "Hijacked", "expected_updated_at": account["updated_at"]},
        headers=bob,
    )
    assert resp.status_code == 404, resp.text

    unchanged = client.get(f"/api/v1/bank-accounts/{account['id']}", headers=alice).json()
    assert unchanged["account_name"] == "Alice's Account"


def test_transfer_between_owned_accounts_updates_both_balances(
    client: TestClient, auth_headers: dict
):
    period_id = _create_period(client, auth_headers, 2034, 1)
    source = _create_account(client, auth_headers, "Checking", opening_balance="500.00")
    destination = _create_account(client, auth_headers, "Savings", opening_balance="100.00")

    resp = client.post(
        "/api/v1/bank-transactions/transfer",
        json={
            "source_bank_account_id": source["id"],
            "destination_bank_account_id": destination["id"],
            "financial_period_id": period_id,
            "amount": "150.00",
            "currency": "GMD",
            "transaction_date": "2034-01-05",
            "description": "Move some cash to savings",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["source_transaction"]["transaction_type"] == "TRANSFER_OUT"
    assert body["destination_transaction"]["transaction_type"] == "TRANSFER_IN"
    assert body["source_transaction"]["transfer_pair_id"] == body["transfer_pair_id"]
    assert body["destination_transaction"]["transfer_pair_id"] == body["transfer_pair_id"]

    source_after = client.get(f"/api/v1/bank-accounts/{source['id']}", headers=auth_headers).json()
    destination_after = client.get(
        f"/api/v1/bank-accounts/{destination['id']}", headers=auth_headers
    ).json()
    assert Decimal(str(source_after["current_balance"])) == Decimal("350.0000")
    assert Decimal(str(destination_after["current_balance"])) == Decimal("250.0000")


def test_transfer_rejects_same_account(client: TestClient, auth_headers: dict):
    period_id = _create_period(client, auth_headers, 2034, 2)
    account = _create_account(client, auth_headers, "Only Account", opening_balance="200.00")

    resp = client.post(
        "/api/v1/bank-transactions/transfer",
        json={
            "source_bank_account_id": account["id"],
            "destination_bank_account_id": account["id"],
            "financial_period_id": period_id,
            "amount": "50.00",
            "currency": "GMD",
            "transaction_date": "2034-02-05",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


def test_transfer_rejects_when_either_account_not_owned_by_user(
    client: TestClient, auth_headers_factory
):
    alice = auth_headers_factory("alice")
    bob = auth_headers_factory("bob")

    period_id = _create_period(client, alice, 2034, 3)
    alice_account = _create_account(client, alice, "Alice Checking", opening_balance="300.00")
    bob_account = _create_account(client, bob, "Bob Checking", opening_balance="300.00")

    # Alice tries to pull money out of Bob's account into her own.
    resp = client.post(
        "/api/v1/bank-transactions/transfer",
        json={
            "source_bank_account_id": bob_account["id"],
            "destination_bank_account_id": alice_account["id"],
            "financial_period_id": period_id,
            "amount": "50.00",
            "currency": "GMD",
            "transaction_date": "2034-03-05",
        },
        headers=alice,
    )
    assert resp.status_code == 404, resp.text

    # Alice tries to send money into Bob's account.
    resp2 = client.post(
        "/api/v1/bank-transactions/transfer",
        json={
            "source_bank_account_id": alice_account["id"],
            "destination_bank_account_id": bob_account["id"],
            "financial_period_id": period_id,
            "amount": "50.00",
            "currency": "GMD",
            "transaction_date": "2034-03-05",
        },
        headers=alice,
    )
    assert resp2.status_code == 404, resp2.text

    # Neither balance moved.
    bob_after = client.get(f"/api/v1/bank-accounts/{bob_account['id']}", headers=bob).json()
    assert Decimal(str(bob_after["current_balance"])) == Decimal("300.0000")


def test_bank_transaction_rejected_on_closed_period(client: TestClient, auth_headers: dict):
    period_id = _create_period(client, auth_headers, 2034, 4)
    account = _create_account(client, auth_headers, "Closed Period Account")

    close_resp = client.post(
        f"/api/v1/financial-periods/{period_id}/close", headers=auth_headers
    )
    assert close_resp.status_code == 200, close_resp.text

    resp = client.post(
        "/api/v1/bank-transactions",
        json={
            "bank_account_id": account["id"],
            "financial_period_id": period_id,
            "transaction_type": "DEPOSIT",
            "amount": "100.00",
            "currency": "GMD",
            "transaction_date": "2034-04-05",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 409, resp.text

    unchanged = client.get(f"/api/v1/bank-accounts/{account['id']}", headers=auth_headers).json()
    assert Decimal(str(unchanged["current_balance"])) == Decimal("0.0000")


def test_bank_transaction_rejected_on_inactive_account(client: TestClient, auth_headers: dict):
    """D-011/spec §38-32: `transfer()` and `SavingsAllocationService.create()` both already
    reject an inactive destination account — plain create() was missing the same check."""
    period_id = _create_period(client, auth_headers, 2034, 5)
    account = _create_account(client, auth_headers, "Soon Inactive")

    deactivate_resp = client.delete(f"/api/v1/bank-accounts/{account['id']}", headers=auth_headers)
    assert deactivate_resp.status_code == 204, deactivate_resp.text

    resp = client.post(
        "/api/v1/bank-transactions",
        json={
            "bank_account_id": account["id"],
            "financial_period_id": period_id,
            "transaction_type": "DEPOSIT",
            "amount": "100.00",
            "currency": "GMD",
            "transaction_date": "2034-05-05",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text

    unchanged = client.get(f"/api/v1/bank-accounts/{account['id']}", headers=auth_headers).json()
    assert Decimal(str(unchanged["current_balance"])) == Decimal("0.0000")
