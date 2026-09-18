"""Phase 3 distribution-rule CRUD: PATCH rule fields (incl. the is_default swap), PUT
categories (row-locked 100% re-validation, D-009; unallocated-bucket swap, D-010), and
soft-delete/deactivate blocked while a rule is an open period's active selection."""
from decimal import Decimal

from fastapi.testclient import TestClient


def _create_rule(client: TestClient, headers: dict, name: str, categories: list) -> dict:
    resp = client.post(
        "/api/v1/distribution-rules",
        json={"name": name, "description": None, "categories": categories},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _two_category_payload():
    return [
        {"name": "Needs", "percentage": "60.00", "contributes_to_automatic_savings": True},
        {"name": "Wants", "percentage": "40.00", "contributes_to_automatic_savings": True},
    ]


def test_update_rule_fields_and_default_swap(client: TestClient, auth_headers: dict):
    rule_a = _create_rule(client, auth_headers, "Rule A", _two_category_payload())
    rule_b = _create_rule(client, auth_headers, "Rule B", _two_category_payload())
    assert rule_a["is_default"] is False
    assert rule_b["is_default"] is False

    set_default_a = client.patch(
        f"/api/v1/distribution-rules/{rule_a['id']}",
        json={"is_default": True, "expected_updated_at": rule_a["updated_at"]},
        headers=auth_headers,
    )
    assert set_default_a.status_code == 200, set_default_a.text
    assert set_default_a.json()["is_default"] is True

    # Setting rule_b as default must unset rule_a's default flag in the same transaction,
    # never surfacing the partial-unique-index violation as a raw 500.
    set_default_b = client.patch(
        f"/api/v1/distribution-rules/{rule_b['id']}",
        json={"is_default": True, "expected_updated_at": rule_b["updated_at"]},
        headers=auth_headers,
    )
    assert set_default_b.status_code == 200, set_default_b.text
    assert set_default_b.json()["is_default"] is True

    rule_a_refetched = client.get(
        f"/api/v1/distribution-rules/{rule_a['id']}", headers=auth_headers
    )
    assert rule_a_refetched.json()["is_default"] is False


def test_update_rule_optimistic_lock_conflict(client: TestClient, auth_headers: dict):
    rule = _create_rule(client, auth_headers, "Rule", _two_category_payload())

    first = client.patch(
        f"/api/v1/distribution-rules/{rule['id']}",
        json={"name": "Renamed once", "expected_updated_at": rule["updated_at"]},
        headers=auth_headers,
    )
    assert first.status_code == 200, first.text

    stale_retry = client.patch(
        f"/api/v1/distribution-rules/{rule['id']}",
        json={"name": "Renamed twice", "expected_updated_at": rule["updated_at"]},
        headers=auth_headers,
    )
    assert stale_retry.status_code == 409, stale_retry.text

    current = client.get(f"/api/v1/distribution-rules/{rule['id']}", headers=auth_headers)
    assert current.json()["name"] == "Renamed once"


def test_replace_categories_rejects_bad_percentage_sum(client: TestClient, auth_headers: dict):
    rule = _create_rule(client, auth_headers, "Rule", _two_category_payload())
    needs_id = next(c["id"] for c in rule["categories"] if c["name"] == "Needs")
    wants_id = next(c["id"] for c in rule["categories"] if c["name"] == "Wants")

    bad_payload = {
        "categories": [
            {"id": needs_id, "name": "Needs", "percentage": "50.00"},
            {"id": wants_id, "name": "Wants", "percentage": "40.00"},
        ],
        "expected_updated_at": rule["updated_at"],
    }
    resp = client.put(
        f"/api/v1/distribution-rules/{rule['id']}/categories", json=bad_payload, headers=auth_headers
    )
    assert resp.status_code == 422, resp.text

    # Rejected at the schema layer before anything touched the row-locked mutation path, so
    # the rule's categories are completely unchanged.
    unchanged = client.get(f"/api/v1/distribution-rules/{rule['id']}", headers=auth_headers)
    percentages = {c["name"]: Decimal(str(c["percentage"])) for c in unchanged.json()["categories"]}
    assert percentages == {"Needs": Decimal("60.00"), "Wants": Decimal("40.00")}


def test_replace_categories_happy_path_add_edit_remove(client: TestClient, auth_headers: dict):
    rule = _create_rule(client, auth_headers, "Rule", _two_category_payload())
    needs_id = next(c["id"] for c in rule["categories"] if c["name"] == "Needs")
    # Drop "Wants", edit "Needs" down to 70%, add a new "Savings" category for the remainder.
    payload = {
        "categories": [
            {"id": needs_id, "name": "Needs", "percentage": "70.00"},
            {"name": "Savings", "percentage": "30.00", "contributes_to_automatic_savings": False},
        ],
        "expected_updated_at": rule["updated_at"],
    }
    resp = client.put(
        f"/api/v1/distribution-rules/{rule['id']}/categories", json=payload, headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    names = {c["name"] for c in updated["categories"]}
    assert names == {"Needs", "Savings"}
    assert updated["updated_at"] != rule["updated_at"]


def test_replace_categories_swaps_unallocated_bucket_without_conflict(
    client: TestClient, auth_headers: dict
):
    rule = _create_rule(
        client,
        auth_headers,
        "Rule",
        [
            {"name": "Needs", "percentage": "60.00", "is_unallocated_bucket": True},
            {"name": "Wants", "percentage": "40.00", "is_unallocated_bucket": False},
        ],
    )
    needs_id = next(c["id"] for c in rule["categories"] if c["name"] == "Needs")
    wants_id = next(c["id"] for c in rule["categories"] if c["name"] == "Wants")

    # Move the unallocated-bucket flag from Needs to Wants in one replace call — must not trip
    # the partial unique index mid-transaction (D-010).
    payload = {
        "categories": [
            {"id": needs_id, "name": "Needs", "percentage": "60.00", "is_unallocated_bucket": False},
            {"id": wants_id, "name": "Wants", "percentage": "40.00", "is_unallocated_bucket": True},
        ],
        "expected_updated_at": rule["updated_at"],
    }
    resp = client.put(
        f"/api/v1/distribution-rules/{rule['id']}/categories", json=payload, headers=auth_headers
    )
    assert resp.status_code == 200, resp.text
    by_name = {c["name"]: c["is_unallocated_bucket"] for c in resp.json()["categories"]}
    assert by_name == {"Needs": False, "Wants": True}


def test_replace_categories_rejects_more_than_one_unallocated_bucket(
    client: TestClient, auth_headers: dict
):
    rule = _create_rule(client, auth_headers, "Rule", _two_category_payload())
    needs_id = next(c["id"] for c in rule["categories"] if c["name"] == "Needs")
    wants_id = next(c["id"] for c in rule["categories"] if c["name"] == "Wants")

    payload = {
        "categories": [
            {"id": needs_id, "name": "Needs", "percentage": "60.00", "is_unallocated_bucket": True},
            {"id": wants_id, "name": "Wants", "percentage": "40.00", "is_unallocated_bucket": True},
        ],
        "expected_updated_at": rule["updated_at"],
    }
    resp = client.put(
        f"/api/v1/distribution-rules/{rule['id']}/categories", json=payload, headers=auth_headers
    )
    assert resp.status_code == 422, resp.text


def test_replace_categories_blocks_removing_category_referenced_by_expense(
    client: TestClient, auth_headers: dict
):
    rule = _create_rule(client, auth_headers, "Rule", _two_category_payload())
    needs_id = next(c["id"] for c in rule["categories"] if c["name"] == "Needs")
    wants_id = next(c["id"] for c in rule["categories"] if c["name"] == "Wants")

    period_resp = client.post(
        "/api/v1/financial-periods", json={"year": 2031, "month": 1}, headers=auth_headers
    )
    assert period_resp.status_code == 201, period_resp.text
    period_id = period_resp.json()["id"]

    select_resp = client.post(
        f"/api/v1/financial-periods/{period_id}/select-distribution-rule",
        json={"distribution_rule_id": rule["id"]},
        headers=auth_headers,
    )
    assert select_resp.status_code == 200, select_resp.text

    expense_resp = client.post(
        "/api/v1/expenses",
        json={
            "financial_period_id": period_id,
            "distribution_category_id": needs_id,
            "name": "Rent",
            "expense_category": "RENT",
            "amount": "100.00",
            "currency": "GMD",
            "expense_date": "2031-01-05",
        },
        headers=auth_headers,
    )
    assert expense_resp.status_code == 201, expense_resp.text

    # Attempting to remove "Needs" (still referenced by the expense above) is rejected.
    payload = {
        "categories": [{"id": wants_id, "name": "Wants", "percentage": "100.00"}],
        "expected_updated_at": rule["updated_at"],
    }
    resp = client.put(
        f"/api/v1/distribution-rules/{rule['id']}/categories", json=payload, headers=auth_headers
    )
    assert resp.status_code == 409, resp.text

    # Keeping "Needs" (even while editing its percentage) still succeeds.
    ok_payload = {
        "categories": [
            {"id": needs_id, "name": "Needs", "percentage": "50.00"},
            {"id": wants_id, "name": "Wants", "percentage": "50.00"},
        ],
        "expected_updated_at": rule["updated_at"],
    }
    ok_resp = client.put(
        f"/api/v1/distribution-rules/{rule['id']}/categories", json=ok_payload, headers=auth_headers
    )
    assert ok_resp.status_code == 200, ok_resp.text


def test_deactivate_rule_blocked_while_selected_by_open_period(
    client: TestClient, auth_headers: dict
):
    rule = _create_rule(client, auth_headers, "Rule", _two_category_payload())
    period_resp = client.post(
        "/api/v1/financial-periods", json={"year": 2031, "month": 2}, headers=auth_headers
    )
    assert period_resp.status_code == 201, period_resp.text
    period_id = period_resp.json()["id"]

    select_resp = client.post(
        f"/api/v1/financial-periods/{period_id}/select-distribution-rule",
        json={"distribution_rule_id": rule["id"]},
        headers=auth_headers,
    )
    assert select_resp.status_code == 200, select_resp.text

    delete_resp = client.delete(f"/api/v1/distribution-rules/{rule['id']}", headers=auth_headers)
    assert delete_resp.status_code == 409, delete_resp.text

    # Same guard applies to the PATCH-based deactivation path (is_active: false).
    deactivate_resp = client.patch(
        f"/api/v1/distribution-rules/{rule['id']}",
        json={"is_active": False, "expected_updated_at": rule["updated_at"]},
        headers=auth_headers,
    )
    assert deactivate_resp.status_code == 409, deactivate_resp.text

    # Closing the period releases the guard.
    close_resp = client.post(f"/api/v1/financial-periods/{period_id}/close", headers=auth_headers)
    assert close_resp.status_code == 200, close_resp.text

    delete_after_close = client.delete(
        f"/api/v1/distribution-rules/{rule['id']}", headers=auth_headers
    )
    assert delete_after_close.status_code == 204, delete_after_close.text
