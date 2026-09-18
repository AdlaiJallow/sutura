"""Regression checks (spec §38) confirming Phase 3's update/validation additions didn't change
pre-existing financial-engine behavior at the API level:

- §38-11: a category overspend is shown as a visible negative remaining balance and never
  steals from automatic savings (only positive remainders are summed) — exercised here through
  the new Expense PATCH endpoint, not just create.
- §38-13: manual savings are computable with zero automatic savings (no income, no distribution
  rule at all) — exercised through the new SavingsItem PATCH endpoint.
"""
from decimal import Decimal

from fastapi.testclient import TestClient


def test_overspent_category_excluded_from_automatic_savings_after_update(
    client: TestClient, auth_headers: dict
):
    period_resp = client.post(
        "/api/v1/financial-periods", json={"year": 2033, "month": 1}, headers=auth_headers
    )
    period_id = period_resp.json()["id"]

    salary_resp = client.post(
        "/api/v1/salaries",
        json={"financial_period_id": period_id, "net_amount": "1000.00", "currency": "GMD"},
        headers=auth_headers,
    )
    assert salary_resp.status_code == 201, salary_resp.text

    rule_resp = client.post(
        "/api/v1/distribution-rules",
        json={"name": "Rule", "categories": [{"name": "Needs", "percentage": "100.00"}]},
        headers=auth_headers,
    )
    assert rule_resp.status_code == 201, rule_resp.text
    rule = rule_resp.json()
    category_id = rule["categories"][0]["id"]

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
            "distribution_category_id": category_id,
            "name": "Rent",
            "expense_category": "RENT",
            "amount": "500.00",
            "currency": "GMD",
            "expense_date": "2033-01-05",
        },
        headers=auth_headers,
    )
    assert expense_resp.status_code == 201, expense_resp.text
    expense = expense_resp.json()

    summary_resp = client.get(
        f"/api/v1/financial-periods/{period_id}/summary", headers=auth_headers
    )
    assert summary_resp.status_code == 200, summary_resp.text
    summary = summary_resp.json()
    # Allocation is 1000, used is 500: still within budget, so automatic savings picks up the
    # positive 500 remainder.
    assert Decimal(str(summary["automatic_savings"])) == Decimal("500.0000")

    # Now push the expense past the category's allocation via the new update endpoint.
    update_resp = client.patch(
        f"/api/v1/expenses/{expense['id']}",
        json={"amount": "1500.00", "expected_updated_at": expense["updated_at"]},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200, update_resp.text

    overspent_summary = client.get(
        f"/api/v1/financial-periods/{period_id}/summary", headers=auth_headers
    ).json()
    # Category remaining is now -500 (1000 allocation - 1500 used): a negative remainder is
    # never summed into automatic savings (only positive remainders count, D-001), and it never
    # "borrows" from another category — it just shows as a shortfall.
    assert Decimal(str(overspent_summary["automatic_savings"])) == Decimal("0.0000")


def test_manual_savings_computable_without_any_automatic_savings(
    client: TestClient, auth_headers: dict
):
    period_resp = client.post(
        "/api/v1/financial-periods", json={"year": 2033, "month": 2}, headers=auth_headers
    )
    period_id = period_resp.json()["id"]

    # No salary, no income, no distribution rule selected at all -> zero automatic savings.
    item_resp = client.post(
        "/api/v1/savings-items",
        json={
            "financial_period_id": period_id,
            "name": "Cash under the mattress",
            "amount": "200.00",
            "currency": "GMD",
            "date": "2033-02-01",
        },
        headers=auth_headers,
    )
    assert item_resp.status_code == 201, item_resp.text
    item = item_resp.json()

    summary = client.get(
        f"/api/v1/financial-periods/{period_id}/summary", headers=auth_headers
    ).json()
    assert Decimal(str(summary["automatic_savings"])) == Decimal("0.0000")
    assert Decimal(str(summary["manual_savings"])) == Decimal("200.0000")
    assert Decimal(str(summary["final_savings"])) == Decimal("200.0000")

    # Editing the manual entry via the new PATCH endpoint keeps final savings computable and
    # correct without any automatic-savings contribution ever appearing.
    update_resp = client.patch(
        f"/api/v1/savings-items/{item['id']}",
        json={"amount": "250.00", "expected_updated_at": item["updated_at"]},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200, update_resp.text

    updated_summary = client.get(
        f"/api/v1/financial-periods/{period_id}/summary", headers=auth_headers
    ).json()
    assert Decimal(str(updated_summary["automatic_savings"])) == Decimal("0.0000")
    assert Decimal(str(updated_summary["manual_savings"])) == Decimal("250.0000")
    assert Decimal(str(updated_summary["final_savings"])) == Decimal("250.0000")
