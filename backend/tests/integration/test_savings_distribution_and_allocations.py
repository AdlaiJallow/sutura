"""Phase 4 (Accounts) coverage for `SavingsDistributionRule`/`SavingsDistributionRuleItem`
(D-013) and `SavingsAllocation` (D-014, spec §19/§20):

- Rule create/update/replace-items with the 100%-sum invariant (D-009-style, applied to
  savings rules).
- An allocation that would over-allocate `Savings.final_savings_total` is rejected outright
  (spec §38-15), never silently clamped.
- A manual allocation to a real bank account creates the linked `BankTransaction` and updates
  the account balance; a `destination_label`-only allocation does not touch the bank ledger
  at all (D-014).
- `apply_rule` replaces the previous AUTO allocations (bulk-deleted, not stacked) while any
  MANUAL allocations are left untouched.
- Cross-user isolation: cannot allocate to another user's bank account (D-020, 404).
"""
from decimal import Decimal

from fastapi.testclient import TestClient


def _create_period(client: TestClient, headers: dict, year: int, month: int) -> str:
    resp = client.post(
        "/api/v1/financial-periods", json={"year": year, "month": month}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_account(client: TestClient, headers: dict, name: str) -> dict:
    resp = client.post(
        "/api/v1/bank-accounts",
        json={"account_name": name, "currency": "GMD", "opening_balance": "0"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _seed_final_savings(client: TestClient, headers: dict, period_id: str, amount: str) -> dict:
    """Simplest way to give a period a non-zero `Savings.final_savings_total` without needing
    a full income + distribution-rule setup: a manual SavingsItem alone drives
    `final_savings = automatic (0) + manual` (see `_compute_summary`). Returns the created
    SavingsItem so a test can later shrink it to simulate final savings dropping below an
    already-allocated total."""
    resp = client.post(
        "/api/v1/savings-items",
        json={
            "financial_period_id": period_id,
            "name": "Manual savings seed",
            "amount": amount,
            "currency": "GMD",
            "date": "2032-01-01",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_rule(client: TestClient, headers: dict, name: str, items: list) -> dict:
    resp = client.post(
        "/api/v1/savings-distribution-rules",
        json={"name": name, "items": items},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_rule_rejects_bad_percentage_sum(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/v1/savings-distribution-rules",
        json={
            "name": "Bad Rule",
            "items": [
                {"destination_label": "Emergency Fund", "percentage": "50.00"},
                {"destination_label": "Vacation Fund", "percentage": "40.00"},
            ],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


def test_create_rule_rejects_item_missing_destination(client: TestClient, auth_headers: dict):
    resp = client.post(
        "/api/v1/savings-distribution-rules",
        json={"name": "No Destination", "items": [{"percentage": "100.00"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


def test_create_and_update_rule_fields_with_default_swap(client: TestClient, auth_headers: dict):
    rule_a = _create_rule(
        client,
        auth_headers,
        "Rule A",
        [{"destination_label": "Emergency Fund", "percentage": "100.00"}],
    )
    rule_b = _create_rule(
        client,
        auth_headers,
        "Rule B",
        [{"destination_label": "Vacation Fund", "percentage": "100.00"}],
    )
    assert rule_a["is_default"] is False

    set_default_a = client.patch(
        f"/api/v1/savings-distribution-rules/{rule_a['id']}",
        json={"is_default": True, "expected_updated_at": rule_a["updated_at"]},
        headers=auth_headers,
    )
    assert set_default_a.status_code == 200, set_default_a.text
    assert set_default_a.json()["is_default"] is True

    set_default_b = client.patch(
        f"/api/v1/savings-distribution-rules/{rule_b['id']}",
        json={"is_default": True, "expected_updated_at": rule_b["updated_at"]},
        headers=auth_headers,
    )
    assert set_default_b.status_code == 200, set_default_b.text

    rule_a_refetched = client.get(
        f"/api/v1/savings-distribution-rules/{rule_a['id']}", headers=auth_headers
    ).json()
    assert rule_a_refetched["is_default"] is False

    stale_retry = client.patch(
        f"/api/v1/savings-distribution-rules/{rule_a['id']}",
        json={"name": "Renamed", "expected_updated_at": rule_a["updated_at"]},
        headers=auth_headers,
    )
    assert stale_retry.status_code == 409, stale_retry.text


def test_replace_items_happy_path_and_bad_sum_rejected(client: TestClient, auth_headers: dict):
    rule = _create_rule(
        client,
        auth_headers,
        "Replaceable Rule",
        [
            {"destination_label": "Emergency Fund", "percentage": "60.00"},
            {"destination_label": "Vacation Fund", "percentage": "40.00"},
        ],
    )
    emergency_id = next(
        i["id"] for i in rule["items"] if i["destination_label"] == "Emergency Fund"
    )

    bad_payload = {
        "items": [
            {"id": emergency_id, "destination_label": "Emergency Fund", "percentage": "60.00"},
            {"destination_label": "New Fund", "percentage": "20.00"},
        ],
        "expected_updated_at": rule["updated_at"],
    }
    bad_resp = client.put(
        f"/api/v1/savings-distribution-rules/{rule['id']}/items",
        json=bad_payload,
        headers=auth_headers,
    )
    assert bad_resp.status_code == 422, bad_resp.text

    good_payload = {
        "items": [
            {"id": emergency_id, "destination_label": "Emergency Fund", "percentage": "70.00"},
            {"destination_label": "New Fund", "percentage": "30.00"},
        ],
        "expected_updated_at": rule["updated_at"],
    }
    good_resp = client.put(
        f"/api/v1/savings-distribution-rules/{rule['id']}/items",
        json=good_payload,
        headers=auth_headers,
    )
    assert good_resp.status_code == 200, good_resp.text
    labels = {i["destination_label"] for i in good_resp.json()["items"]}
    assert labels == {"Emergency Fund", "New Fund"}


def test_rule_item_bank_account_must_be_owned_and_active(
    client: TestClient, auth_headers_factory
):
    alice = auth_headers_factory("alice")
    bob = auth_headers_factory("bob")
    bob_account = _create_account(client, bob, "Bob's Account")

    resp = client.post(
        "/api/v1/savings-distribution-rules",
        json={
            "name": "Cross user rule",
            "items": [{"bank_account_id": bob_account["id"], "percentage": "100.00"}],
        },
        headers=alice,
    )
    assert resp.status_code == 404, resp.text


def test_allocation_over_allocation_is_rejected(client: TestClient, auth_headers: dict):
    period_id = _create_period(client, auth_headers, 2032, 1)
    _seed_final_savings(client, auth_headers, period_id, "200.00")

    ok_resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "destination_label": "Emergency Fund",
            "amount": "150.00",
        },
        headers=auth_headers,
    )
    assert ok_resp.status_code == 201, ok_resp.text

    over_resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "destination_label": "Vacation Fund",
            "amount": "100.00",
        },
        headers=auth_headers,
    )
    assert over_resp.status_code == 409, over_resp.text

    # Nothing partially applied — only the first (150.00) allocation exists.
    list_resp = client.get(
        f"/api/v1/savings-allocations?financial_period_id={period_id}", headers=auth_headers
    )
    assert list_resp.status_code == 200, list_resp.text
    amounts = [Decimal(str(a["amount"])) for a in list_resp.json()["data"]]
    assert amounts == [Decimal("150.0000")]


def test_manual_allocation_to_real_bank_account_creates_bank_transaction(
    client: TestClient, auth_headers: dict
):
    period_id = _create_period(client, auth_headers, 2032, 2)
    _seed_final_savings(client, auth_headers, period_id, "500.00")
    account = _create_account(client, auth_headers, "Savings Vault")

    alloc_resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "bank_account_id": account["id"],
            "amount": "300.00",
            "transaction_date": "2032-02-10",
        },
        headers=auth_headers,
    )
    assert alloc_resp.status_code == 201, alloc_resp.text
    allocation = alloc_resp.json()
    assert allocation["bank_transaction_id"] is not None
    assert allocation["allocation_method"] == "MANUAL"

    account_after = client.get(
        f"/api/v1/bank-accounts/{account['id']}", headers=auth_headers
    ).json()
    assert Decimal(str(account_after["current_balance"])) == Decimal("300.0000")

    txn_resp = client.get(
        f"/api/v1/bank-transactions/{allocation['bank_transaction_id']}", headers=auth_headers
    )
    assert txn_resp.status_code == 200, txn_resp.text
    txn = txn_resp.json()
    assert txn["transaction_type"] == "DEPOSIT"
    assert txn["related_record_type"] == "SAVINGS_ALLOCATION"
    assert txn["related_record_id"] == allocation["id"]
    assert Decimal(str(txn["amount"])) == Decimal("300.0000")


def test_destination_label_only_allocation_creates_no_bank_transaction(
    client: TestClient, auth_headers: dict
):
    period_id = _create_period(client, auth_headers, 2032, 3)
    _seed_final_savings(client, auth_headers, period_id, "400.00")

    alloc_resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "destination_label": "Emergency Fund",
            "amount": "250.00",
        },
        headers=auth_headers,
    )
    assert alloc_resp.status_code == 201, alloc_resp.text
    allocation = alloc_resp.json()
    assert allocation["bank_transaction_id"] is None
    assert allocation["bank_account_id"] is None
    assert allocation["destination_label"] == "Emergency Fund"


def test_allocation_requires_a_destination(client: TestClient, auth_headers: dict):
    period_id = _create_period(client, auth_headers, 2032, 4)
    resp = client.post(
        "/api/v1/savings-allocations",
        json={"financial_period_id": period_id, "amount": "10.00"},
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


def test_apply_rule_replaces_auto_allocations_and_leaves_manual_untouched(
    client: TestClient, auth_headers: dict
):
    period_id = _create_period(client, auth_headers, 2032, 5)
    _seed_final_savings(client, auth_headers, period_id, "1000.00")

    # One manual allocation first: 200 of the 1000 final savings.
    manual_resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "destination_label": "Manual Pick",
            "amount": "200.00",
        },
        headers=auth_headers,
    )
    assert manual_resp.status_code == 201, manual_resp.text
    manual_id = manual_resp.json()["id"]

    rule = _create_rule(
        client,
        auth_headers,
        "Split Rule",
        [
            {"destination_label": "Emergency Fund", "percentage": "60.00"},
            {"destination_label": "Vacation Fund", "percentage": "40.00"},
        ],
    )

    apply_resp = client.post(
        "/api/v1/savings-allocations/apply-rule",
        json={"financial_period_id": period_id, "savings_distribution_rule_id": rule["id"]},
        headers=auth_headers,
    )
    assert apply_resp.status_code == 200, apply_resp.text
    first_auto = apply_resp.json()
    # Remaining after the 200 manual allocation is 800: 60/40 split => 480 / 320.
    by_label = {a["destination_label"]: Decimal(str(a["amount"])) for a in first_auto}
    assert by_label == {"Emergency Fund": Decimal("480.0000"), "Vacation Fund": Decimal("320.0000")}
    assert all(a["allocation_method"] == "AUTO" for a in first_auto)
    assert all(a["bank_transaction_id"] is None for a in first_auto)

    # Applying again must replace the AUTO set (not stack it) and leave the MANUAL row alone.
    second_apply_resp = client.post(
        "/api/v1/savings-allocations/apply-rule",
        json={"financial_period_id": period_id, "savings_distribution_rule_id": rule["id"]},
        headers=auth_headers,
    )
    assert second_apply_resp.status_code == 200, second_apply_resp.text

    all_resp = client.get(
        f"/api/v1/savings-allocations?financial_period_id={period_id}&page_size=100",
        headers=auth_headers,
    )
    assert all_resp.status_code == 200, all_resp.text
    all_allocations = all_resp.json()["data"]
    auto_rows = [a for a in all_allocations if a["allocation_method"] == "AUTO"]
    manual_rows = [a for a in all_allocations if a["allocation_method"] == "MANUAL"]

    assert len(auto_rows) == 2  # replaced, not stacked (would be 4 if stacked)
    assert len(manual_rows) == 1
    assert manual_rows[0]["id"] == manual_id
    assert Decimal(str(manual_rows[0]["amount"])) == Decimal("200.0000")

    total = sum(Decimal(str(a["amount"])) for a in all_allocations)
    assert total == Decimal("1000.0000")


def test_apply_rule_rejects_when_manual_already_exceeds_final_savings(
    client: TestClient, auth_headers: dict
):
    """MANUAL allocations can never exceed `final_savings_total` *at the moment they're
    created* (create() checks this). But `final_savings_total` can shrink afterwards (e.g. the
    underlying manual SavingsItem is edited down), leaving previously-valid MANUAL allocations
    now exceeding the new, lower total — `apply_rule` must detect that and refuse to run rather
    than generate a negative/clamped AUTO split."""
    period_id = _create_period(client, auth_headers, 2032, 6)
    savings_item = _seed_final_savings(client, auth_headers, period_id, "200.00")

    manual_resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "destination_label": "All of it",
            "amount": "200.00",
        },
        headers=auth_headers,
    )
    assert manual_resp.status_code == 201, manual_resp.text

    # Shrink the manual savings item so final_savings_total (100) now sits below the 200
    # already allocated.
    shrink_resp = client.patch(
        f"/api/v1/savings-items/{savings_item['id']}",
        json={"amount": "100.00", "expected_updated_at": savings_item["updated_at"]},
        headers=auth_headers,
    )
    assert shrink_resp.status_code == 200, shrink_resp.text

    # D-023: refreshing the Savings cache (via the period summary's live recompute for an
    # OPEN period) with distributed_total (200) now exceeding the shrunk final_savings_total
    # (100) must persist the true negative undistributed_total — visibly, like an overspent
    # category — not crash and not silently clamp to zero.
    summary_resp = client.get(f"/api/v1/financial-periods/{period_id}/summary", headers=auth_headers)
    assert summary_resp.status_code == 200, summary_resp.text
    assert Decimal(str(summary_resp.json()["undistributed_savings"])) == Decimal("-100.0000")

    rule = _create_rule(
        client, auth_headers, "Overflow Rule", [{"destination_label": "X", "percentage": "100.00"}]
    )
    apply_resp = client.post(
        "/api/v1/savings-allocations/apply-rule",
        json={"financial_period_id": period_id, "savings_distribution_rule_id": rule["id"]},
        headers=auth_headers,
    )
    assert apply_resp.status_code == 409, apply_resp.text


def test_delete_auto_allocation_individually_is_rejected(client: TestClient, auth_headers: dict):
    period_id = _create_period(client, auth_headers, 2032, 7)
    _seed_final_savings(client, auth_headers, period_id, "300.00")
    rule = _create_rule(
        client, auth_headers, "Single Item Rule", [{"destination_label": "Only", "percentage": "100.00"}]
    )
    apply_resp = client.post(
        "/api/v1/savings-allocations/apply-rule",
        json={"financial_period_id": period_id, "savings_distribution_rule_id": rule["id"]},
        headers=auth_headers,
    )
    assert apply_resp.status_code == 200, apply_resp.text
    auto_id = apply_resp.json()[0]["id"]

    delete_resp = client.delete(f"/api/v1/savings-allocations/{auto_id}", headers=auth_headers)
    assert delete_resp.status_code == 422, delete_resp.text


def test_delete_manual_allocation_while_open(client: TestClient, auth_headers: dict):
    period_id = _create_period(client, auth_headers, 2032, 8)
    _seed_final_savings(client, auth_headers, period_id, "150.00")

    alloc_resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "destination_label": "Temp",
            "amount": "100.00",
        },
        headers=auth_headers,
    )
    assert alloc_resp.status_code == 201, alloc_resp.text
    allocation_id = alloc_resp.json()["id"]

    delete_resp = client.delete(
        f"/api/v1/savings-allocations/{allocation_id}", headers=auth_headers
    )
    assert delete_resp.status_code == 204, delete_resp.text

    get_resp = client.get(f"/api/v1/savings-allocations/{allocation_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_cross_user_cannot_allocate_to_another_users_bank_account(
    client: TestClient, auth_headers_factory
):
    alice = auth_headers_factory("alice")
    bob = auth_headers_factory("bob")

    period_id = _create_period(client, alice, 2032, 9)
    _seed_final_savings(client, alice, period_id, "500.00")
    bob_account = _create_account(client, bob, "Bob's Vault")

    resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "bank_account_id": bob_account["id"],
            "amount": "100.00",
        },
        headers=alice,
    )
    assert resp.status_code == 404, resp.text

    bob_account_after = client.get(
        f"/api/v1/bank-accounts/{bob_account['id']}", headers=bob
    ).json()
    assert Decimal(str(bob_account_after["current_balance"])) == Decimal("0.0000")


def test_cross_user_cannot_fetch_another_users_savings_allocation(
    client: TestClient, auth_headers_factory
):
    alice = auth_headers_factory("alice")
    bob = auth_headers_factory("bob")

    period_id = _create_period(client, alice, 2032, 10)
    _seed_final_savings(client, alice, period_id, "500.00")
    alloc_resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "destination_label": "Alice's Fund",
            "amount": "50.00",
        },
        headers=alice,
    )
    assert alloc_resp.status_code == 201, alloc_resp.text
    allocation_id = alloc_resp.json()["id"]

    cross_resp = client.get(f"/api/v1/savings-allocations/{allocation_id}", headers=bob)
    assert cross_resp.status_code == 404, cross_resp.text
