"""Coverage for `GET /api/v1/distributions/{period_id}` — the read-only per-category
allocation/used/remaining view (docs/api-contract.md §9), added to close the gap the web
frontend flagged: `/distribution-rules` only exposes CRUD (name + percentage), never a period's
computed amounts, and the frontend must never compute money itself (CLAUDE.md).

- No distribution rule selected on the period -> 200 (not 404), zeroed/empty response, but a
  real `total_monthly_income`.
- The spec §40 worked example end to end via real API calls: salary + allowances + other income
  -> D14,000, 50/30/20 split -> allocation/used/remaining per category match exactly.
- An expense pushed above a category's allocation -> negative `remaining`, `is_overspent: true`,
  never clamped (spec §13).
- Cross-user access to another user's period's distribution view -> 404 (D-020).
"""
from decimal import Decimal

from fastapi.testclient import TestClient


def _create_period(client: TestClient, headers: dict, year: int, month: int) -> str:
    resp = client.post(
        "/api/v1/financial-periods", json={"year": year, "month": month}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_rule_50_30_20(client: TestClient, headers: dict) -> dict:
    resp = client.post(
        "/api/v1/distribution-rules",
        json={
            "name": "50/30/20",
            "categories": [
                {"name": "Needs", "percentage": "50.00"},
                {"name": "Wants", "percentage": "30.00"},
                {"name": "Savings Bucket", "percentage": "20.00"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _select_rule(client: TestClient, headers: dict, period_id: str, rule_id: str) -> None:
    resp = client.post(
        f"/api/v1/financial-periods/{period_id}/select-distribution-rule",
        json={"distribution_rule_id": rule_id},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text


def _seed_worked_example_income(client: TestClient, headers: dict, period_id: str) -> None:
    resp = client.post(
        "/api/v1/salaries",
        json={"financial_period_id": period_id, "net_amount": "10000", "currency": "GMD"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    for amount in ("2000", "1000"):
        resp = client.post(
            "/api/v1/allowances",
            json={
                "financial_period_id": period_id,
                "name": "Housing",
                "amount": amount,
                "currency": "GMD",
                "date_received": "2032-01-01",
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text

    for amount in ("500", "500"):
        resp = client.post(
            "/api/v1/income",
            json={
                "financial_period_id": period_id,
                "income_type": "FREELANCE",
                "description": "Side gig",
                "amount": amount,
                "currency": "GMD",
                "date_received": "2032-01-01",
            },
            headers=headers,
        )
        assert resp.status_code == 201, resp.text


def _create_expense(
    client: TestClient, headers: dict, period_id: str, category_id: str, amount: str
) -> dict:
    resp = client.post(
        "/api/v1/expenses",
        json={
            "financial_period_id": period_id,
            "distribution_category_id": category_id,
            "name": "Test expense",
            "expense_category": "OTHER",
            "amount": amount,
            "currency": "GMD",
            "expense_date": "2032-01-15",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_no_rule_selected_returns_200_with_empty_zeroed_response(
    client: TestClient, auth_headers: dict
):
    period_id = _create_period(client, auth_headers, 2032, 1)

    resp = client.get(f"/api/v1/distributions/{period_id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["financial_period_id"] == period_id
    assert body["distribution_rule_id"] is None
    assert body["distribution_rule_name"] is None
    assert body["categories"] == []
    assert Decimal(str(body["total_allocation"])) == Decimal("0.0000")
    assert Decimal(str(body["total_used"])) == Decimal("0.0000")
    assert Decimal(str(body["total_remaining"])) == Decimal("0.0000")
    # total_monthly_income is real even with no rule selected — the period is otherwise empty
    # here, so it is legitimately zero too, but it is not hardcoded/short-circuited.
    assert Decimal(str(body["total_monthly_income"])) == Decimal("0.0000")


def test_worked_example_spec_40_categories_match_exactly(client: TestClient, auth_headers: dict):
    period_id = _create_period(client, auth_headers, 2032, 2)
    _seed_worked_example_income(client, auth_headers, period_id)

    rule = _create_rule_50_30_20(client, auth_headers)
    _select_rule(client, auth_headers, period_id, rule["id"])

    categories_by_name = {c["name"]: c for c in rule["categories"]}
    needs_id = categories_by_name["Needs"]["id"]
    wants_id = categories_by_name["Wants"]["id"]
    savings_bucket_id = categories_by_name["Savings Bucket"]["id"]

    _create_expense(client, auth_headers, period_id, needs_id, "6500")
    _create_expense(client, auth_headers, period_id, wants_id, "3900")
    _create_expense(client, auth_headers, period_id, savings_bucket_id, "2300")

    resp = client.get(f"/api/v1/distributions/{period_id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["distribution_rule_id"] == rule["id"]
    assert body["distribution_rule_name"] == "50/30/20"
    assert Decimal(str(body["total_monthly_income"])) == Decimal("14000.0000")

    by_name = {c["name"]: c for c in body["categories"]}
    assert Decimal(str(by_name["Needs"]["allocation"])) == Decimal("7000.0000")
    assert Decimal(str(by_name["Needs"]["used"])) == Decimal("6500.0000")
    assert Decimal(str(by_name["Needs"]["remaining"])) == Decimal("500.0000")
    assert by_name["Needs"]["is_overspent"] is False

    assert Decimal(str(by_name["Wants"]["allocation"])) == Decimal("4200.0000")
    assert Decimal(str(by_name["Wants"]["used"])) == Decimal("3900.0000")
    assert Decimal(str(by_name["Wants"]["remaining"])) == Decimal("300.0000")

    assert Decimal(str(by_name["Savings Bucket"]["allocation"])) == Decimal("2800.0000")
    assert Decimal(str(by_name["Savings Bucket"]["used"])) == Decimal("2300.0000")
    assert Decimal(str(by_name["Savings Bucket"]["remaining"])) == Decimal("500.0000")

    assert Decimal(str(body["total_allocation"])) == Decimal("14000.0000")
    assert Decimal(str(body["total_used"])) == Decimal("12700.0000")
    assert Decimal(str(body["total_remaining"])) == Decimal("1300.0000")


def test_overspent_category_shows_negative_remaining_not_clamped(
    client: TestClient, auth_headers: dict
):
    period_id = _create_period(client, auth_headers, 2032, 3)
    _seed_worked_example_income(client, auth_headers, period_id)

    rule = _create_rule_50_30_20(client, auth_headers)
    _select_rule(client, auth_headers, period_id, rule["id"])
    needs_id = next(c["id"] for c in rule["categories"] if c["name"] == "Needs")

    # Needs allocation is 7000 (50% of 14000); spend 7500 to push it into overspend.
    _create_expense(client, auth_headers, period_id, needs_id, "7500")

    resp = client.get(f"/api/v1/distributions/{period_id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    needs = next(c for c in resp.json()["categories"] if c["name"] == "Needs")
    assert Decimal(str(needs["remaining"])) == Decimal("-500.0000")
    assert needs["is_overspent"] is True


def test_cross_user_cannot_view_another_users_distribution(
    client: TestClient, auth_headers_factory
):
    alice = auth_headers_factory("alice")
    bob = auth_headers_factory("bob")

    period_id = _create_period(client, alice, 2032, 4)

    resp = client.get(f"/api/v1/distributions/{period_id}", headers=bob)
    assert resp.status_code == 404, resp.text
