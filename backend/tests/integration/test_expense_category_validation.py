"""Expense.distribution_category_id validated against the period's selected distribution rule
(D-006 ERD note), enforced in the service layer on both create and update — not just via the
raw DB foreign key."""
from fastapi.testclient import TestClient


def _create_rule(client: TestClient, headers: dict, name: str, category_name: str) -> dict:
    resp = client.post(
        "/api/v1/distribution-rules",
        json={
            "name": name,
            "categories": [{"name": category_name, "percentage": "100.00"}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_expense_without_category_succeeds_when_no_rule_selected(
    client: TestClient, auth_headers: dict
):
    period_resp = client.post(
        "/api/v1/financial-periods", json={"year": 2032, "month": 1}, headers=auth_headers
    )
    period_id = period_resp.json()["id"]

    resp = client.post(
        "/api/v1/expenses",
        json={
            "financial_period_id": period_id,
            "name": "Transport",
            "expense_category": "TRANSPORTATION",
            "amount": "20.00",
            "currency": "GMD",
            "expense_date": "2032-01-10",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["distribution_category_id"] is None


def test_expense_without_category_fails_once_rule_selected(
    client: TestClient, auth_headers: dict
):
    rule = _create_rule(client, auth_headers, "Rule", "Needs")
    period_resp = client.post(
        "/api/v1/financial-periods", json={"year": 2032, "month": 2}, headers=auth_headers
    )
    period_id = period_resp.json()["id"]

    select_resp = client.post(
        f"/api/v1/financial-periods/{period_id}/select-distribution-rule",
        json={"distribution_rule_id": rule["id"]},
        headers=auth_headers,
    )
    assert select_resp.status_code == 200, select_resp.text

    resp = client.post(
        "/api/v1/expenses",
        json={
            "financial_period_id": period_id,
            "name": "Transport",
            "expense_category": "TRANSPORTATION",
            "amount": "20.00",
            "currency": "GMD",
            "expense_date": "2032-02-10",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


def test_expense_rejects_category_from_a_different_rule(client: TestClient, auth_headers: dict):
    rule_a = _create_rule(client, auth_headers, "Rule A", "Needs")
    rule_b = _create_rule(client, auth_headers, "Rule B", "Wants")
    other_rule_category_id = rule_b["categories"][0]["id"]

    period_resp = client.post(
        "/api/v1/financial-periods", json={"year": 2032, "month": 3}, headers=auth_headers
    )
    period_id = period_resp.json()["id"]
    select_resp = client.post(
        f"/api/v1/financial-periods/{period_id}/select-distribution-rule",
        json={"distribution_rule_id": rule_a["id"]},
        headers=auth_headers,
    )
    assert select_resp.status_code == 200, select_resp.text

    resp = client.post(
        "/api/v1/expenses",
        json={
            "financial_period_id": period_id,
            "distribution_category_id": other_rule_category_id,
            "name": "Groceries",
            "expense_category": "FOOD",
            "amount": "20.00",
            "currency": "GMD",
            "expense_date": "2032-03-10",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text


def test_expense_accepts_category_from_the_selected_rule(client: TestClient, auth_headers: dict):
    rule = _create_rule(client, auth_headers, "Rule", "Needs")
    category_id = rule["categories"][0]["id"]

    period_resp = client.post(
        "/api/v1/financial-periods", json={"year": 2032, "month": 4}, headers=auth_headers
    )
    period_id = period_resp.json()["id"]
    select_resp = client.post(
        f"/api/v1/financial-periods/{period_id}/select-distribution-rule",
        json={"distribution_rule_id": rule["id"]},
        headers=auth_headers,
    )
    assert select_resp.status_code == 200, select_resp.text

    resp = client.post(
        "/api/v1/expenses",
        json={
            "financial_period_id": period_id,
            "distribution_category_id": category_id,
            "name": "Groceries",
            "expense_category": "FOOD",
            "amount": "20.00",
            "currency": "GMD",
            "expense_date": "2032-04-10",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["distribution_category_id"] == category_id


def test_expense_update_revalidates_distribution_category(client: TestClient, auth_headers: dict):
    rule_a = _create_rule(client, auth_headers, "Rule A", "Needs")
    rule_b = _create_rule(client, auth_headers, "Rule B", "Wants")
    category_a = rule_a["categories"][0]["id"]
    category_b = rule_b["categories"][0]["id"]

    period_resp = client.post(
        "/api/v1/financial-periods", json={"year": 2032, "month": 5}, headers=auth_headers
    )
    period_id = period_resp.json()["id"]
    select_resp = client.post(
        f"/api/v1/financial-periods/{period_id}/select-distribution-rule",
        json={"distribution_rule_id": rule_a["id"]},
        headers=auth_headers,
    )
    assert select_resp.status_code == 200, select_resp.text

    create_resp = client.post(
        "/api/v1/expenses",
        json={
            "financial_period_id": period_id,
            "distribution_category_id": category_a,
            "name": "Groceries",
            "expense_category": "FOOD",
            "amount": "20.00",
            "currency": "GMD",
            "expense_date": "2032-05-10",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    expense = create_resp.json()

    # Trying to move it to a category belonging to a different (unselected) rule is rejected.
    bad_update = client.patch(
        f"/api/v1/expenses/{expense['id']}",
        json={
            "distribution_category_id": category_b,
            "expected_updated_at": expense["updated_at"],
        },
        headers=auth_headers,
    )
    assert bad_update.status_code == 422, bad_update.text

    # Clearing it entirely is also rejected, since the period still has a rule selected.
    clear_update = client.patch(
        f"/api/v1/expenses/{expense['id']}",
        json={
            "distribution_category_id": None,
            "expected_updated_at": expense["updated_at"],
        },
        headers=auth_headers,
    )
    assert clear_update.status_code == 422, clear_update.text

    # An unrelated field update leaves the (still-valid) category alone and succeeds.
    rename_update = client.patch(
        f"/api/v1/expenses/{expense['id']}",
        json={"name": "Weekly groceries", "expected_updated_at": expense["updated_at"]},
        headers=auth_headers,
    )
    assert rename_update.status_code == 200, rename_update.text
    assert rename_update.json()["distribution_category_id"] == category_a
