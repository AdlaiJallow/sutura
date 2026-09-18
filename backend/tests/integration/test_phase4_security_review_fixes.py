"""Coverage for the Phase 4 (Accounts) security review fix task (F-1..F-4 + two smaller
items). See docs/decisions.md D-024/D-025 for the judgment calls this depends on.

- F-1 (D-025): `BankAccount.current_balance` mutations are now row-locked
  (`SELECT ... FOR UPDATE`) in `BankTransactionService.create`/`.transfer` and
  `SavingsAllocationService.create`. True multi-connection concurrency isn't exercisable in
  this test harness (each test runs inside one outer DB transaction/session — see
  tests/conftest.py's docstring), so this proves the lock is acquired via
  `BankAccountRepository.lock_owned` directly, and that a sequence of balance-affecting writes
  against the same account (including a back-and-forth transfer pair, which exercises the
  sorted lock-ordering path) always lands on the mathematically correct final balance.
- F-2: `Expense.bank_account_id` must belong to the requesting user on both create and update.
- F-3: transaction/transfer `currency` must match the bank account's own `currency`, never
  trusted as an independent client-supplied field.
- F-4: a `SavingsAllocation` that posts a `BankTransaction` audits that `BankTransaction` too,
  cross-referenced via `bank_transaction_id` in the `SavingsAllocation` audit's `after_state`.
- Smaller item: `SavingsAllocationService.apply_rule` rejects an inactive
  `SavingsDistributionRule`.
"""
import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.banks.models import BankAccount
from app.banks.repository import BankAccountRepository


def _create_period(client: TestClient, headers: dict, year: int, month: int) -> str:
    resp = client.post(
        "/api/v1/financial-periods", json={"year": year, "month": month}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_account(
    client: TestClient,
    headers: dict,
    name: str,
    opening_balance: str = "0",
    currency: str = "GMD",
) -> dict:
    resp = client.post(
        "/api/v1/bank-accounts",
        json={
            "account_name": name,
            "currency": currency,
            "opening_balance": opening_balance,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------------- F-1


def test_lock_owned_returns_the_account_row(db_session: Session, client: TestClient, auth_headers: dict):
    """Direct repository-level check that `lock_owned` exists, is scoped by user_id (D-020),
    and returns the same row `get_owned` would — i.e. it is a safe drop-in everywhere a
    balance-mutating read used to call `get_owned`."""
    account = _create_account(client, auth_headers, "Lock Target", opening_balance="50.00")
    account_id = uuid.UUID(account["id"])

    # Find the underlying user_id via the ORM row itself (client fixture and db_session share
    # the same underlying connection per tests/conftest.py).
    row = db_session.get(BankAccount, account_id)
    assert row is not None

    repo = BankAccountRepository(db_session)
    locked = repo.lock_owned(row.user_id, account_id)
    assert locked is not None
    assert locked.id == account_id
    assert Decimal(locked.current_balance) == Decimal("50.0000")

    # Not owned by a random other user id -> None, same as get_owned (D-020).
    assert repo.lock_owned(uuid.uuid4(), account_id) is None


def test_sequential_deposits_and_withdrawals_never_lose_an_update(
    client: TestClient, auth_headers: dict
):
    """Not true concurrency (single test harness transaction), but proves the row-locked
    read-modify-write sequence in `BankTransactionService.create` is still arithmetically
    correct across a run of several balance-affecting writes against the same account —
    exactly what would silently break under the pre-fix plain-SELECT race."""
    period_id = _create_period(client, auth_headers, 2035, 1)
    account = _create_account(client, auth_headers, "Busy Account", opening_balance="100.00")

    ops = [("DEPOSIT", "10.00"), ("DEPOSIT", "25.00"), ("WITHDRAWAL", "5.00"), ("DEPOSIT", "40.00"), ("WITHDRAWAL", "15.00")]
    for i, (txn_type, amount) in enumerate(ops):
        resp = client.post(
            "/api/v1/bank-transactions",
            json={
                "bank_account_id": account["id"],
                "financial_period_id": period_id,
                "transaction_type": txn_type,
                "amount": amount,
                "currency": "GMD",
                "transaction_date": f"2035-01-{i + 1:02d}",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text

    # 100 + 10 + 25 - 5 + 40 - 15 = 155
    final = client.get(f"/api/v1/bank-accounts/{account['id']}", headers=auth_headers).json()
    assert Decimal(str(final["current_balance"])) == Decimal("155.0000")


def test_back_and_forth_transfers_land_on_correct_balances(client: TestClient, auth_headers: dict):
    """Exercises the sorted-by-account-id lock ordering in `transfer()`: two transfers run in
    opposite directions between the same pair of accounts. Sequentially (this harness can't
    prove deadlock-freedom directly), but the lock-ordering code path is identical regardless
    of which account is source vs. destination, and the resulting balances must still be
    exactly correct."""
    period_id = _create_period(client, auth_headers, 2035, 2)
    account_a = _create_account(client, auth_headers, "A", opening_balance="200.00")
    account_b = _create_account(client, auth_headers, "B", opening_balance="200.00")

    resp1 = client.post(
        "/api/v1/bank-transactions/transfer",
        json={
            "source_bank_account_id": account_a["id"],
            "destination_bank_account_id": account_b["id"],
            "financial_period_id": period_id,
            "amount": "50.00",
            "currency": "GMD",
            "transaction_date": "2035-02-01",
        },
        headers=auth_headers,
    )
    assert resp1.status_code == 201, resp1.text

    # Now the reverse direction — same two accounts, source/destination roles swapped, so the
    # id-sorted lock order acquires the *same first lock* as resp1 did, not the reverse.
    resp2 = client.post(
        "/api/v1/bank-transactions/transfer",
        json={
            "source_bank_account_id": account_b["id"],
            "destination_bank_account_id": account_a["id"],
            "financial_period_id": period_id,
            "amount": "30.00",
            "currency": "GMD",
            "transaction_date": "2035-02-02",
        },
        headers=auth_headers,
    )
    assert resp2.status_code == 201, resp2.text

    a_after = client.get(f"/api/v1/bank-accounts/{account_a['id']}", headers=auth_headers).json()
    b_after = client.get(f"/api/v1/bank-accounts/{account_b['id']}", headers=auth_headers).json()
    # A: 200 - 50 + 30 = 180 ; B: 200 + 50 - 30 = 220
    assert Decimal(str(a_after["current_balance"])) == Decimal("180.0000")
    assert Decimal(str(b_after["current_balance"])) == Decimal("220.0000")


def test_savings_allocation_posting_locks_the_account(client: TestClient, auth_headers: dict):
    """`SavingsAllocationService.create`'s bank-posting branch also locks the account before
    mutating `current_balance`; a prior manual deposit followed by an allocation-triggered
    deposit must both land correctly."""
    period_id = _create_period(client, auth_headers, 2035, 3)
    account = _create_account(client, auth_headers, "Vault", opening_balance="0")

    deposit_resp = client.post(
        "/api/v1/bank-transactions",
        json={
            "bank_account_id": account["id"],
            "financial_period_id": period_id,
            "transaction_type": "DEPOSIT",
            "amount": "20.00",
            "currency": "GMD",
            "transaction_date": "2035-03-01",
        },
        headers=auth_headers,
    )
    assert deposit_resp.status_code == 201, deposit_resp.text

    savings_item_resp = client.post(
        "/api/v1/savings-items",
        json={
            "financial_period_id": period_id,
            "name": "Manual seed",
            "amount": "500.00",
            "currency": "GMD",
            "date": "2035-03-01",
        },
        headers=auth_headers,
    )
    assert savings_item_resp.status_code == 201, savings_item_resp.text

    alloc_resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "bank_account_id": account["id"],
            "amount": "100.00",
            "transaction_date": "2035-03-02",
        },
        headers=auth_headers,
    )
    assert alloc_resp.status_code == 201, alloc_resp.text

    final = client.get(f"/api/v1/bank-accounts/{account['id']}", headers=auth_headers).json()
    assert Decimal(str(final["current_balance"])) == Decimal("120.0000")


# ---------------------------------------------------------------------------------- F-2


def test_expense_create_rejects_another_users_bank_account(
    client: TestClient, auth_headers_factory
):
    alice = auth_headers_factory("alice")
    bob = auth_headers_factory("bob")
    bob_account = _create_account(client, bob, "Bob's Account")

    period_id = _create_period(client, alice, 2035, 4)
    resp = client.post(
        "/api/v1/expenses",
        json={
            "financial_period_id": period_id,
            "name": "Groceries",
            "expense_category": "FOOD",
            "amount": "20.00",
            "currency": "GMD",
            "expense_date": "2035-04-01",
            "bank_account_id": bob_account["id"],
        },
        headers=alice,
    )
    assert resp.status_code == 404, resp.text


def test_expense_create_accepts_own_bank_account(client: TestClient, auth_headers: dict):
    period_id = _create_period(client, auth_headers, 2035, 5)
    account = _create_account(client, auth_headers, "My Account")

    resp = client.post(
        "/api/v1/expenses",
        json={
            "financial_period_id": period_id,
            "name": "Groceries",
            "expense_category": "FOOD",
            "amount": "20.00",
            "currency": "GMD",
            "expense_date": "2035-05-01",
            "bank_account_id": account["id"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["bank_account_id"] == account["id"]


def test_expense_update_rejects_another_users_bank_account(
    client: TestClient, auth_headers_factory
):
    alice = auth_headers_factory("alice")
    bob = auth_headers_factory("bob")
    bob_account = _create_account(client, bob, "Bob's Account 2")

    period_id = _create_period(client, alice, 2035, 6)
    create_resp = client.post(
        "/api/v1/expenses",
        json={
            "financial_period_id": period_id,
            "name": "Transport",
            "expense_category": "TRANSPORTATION",
            "amount": "10.00",
            "currency": "GMD",
            "expense_date": "2035-06-01",
        },
        headers=alice,
    )
    assert create_resp.status_code == 201, create_resp.text
    expense = create_resp.json()

    update_resp = client.patch(
        f"/api/v1/expenses/{expense['id']}",
        json={
            "bank_account_id": bob_account["id"],
            "expected_updated_at": expense["updated_at"],
        },
        headers=alice,
    )
    assert update_resp.status_code == 404, update_resp.text


def test_expense_update_accepts_own_bank_account(client: TestClient, auth_headers: dict):
    period_id = _create_period(client, auth_headers, 2035, 7)
    account = _create_account(client, auth_headers, "Own Account")
    create_resp = client.post(
        "/api/v1/expenses",
        json={
            "financial_period_id": period_id,
            "name": "Transport",
            "expense_category": "TRANSPORTATION",
            "amount": "10.00",
            "currency": "GMD",
            "expense_date": "2035-07-01",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    expense = create_resp.json()

    update_resp = client.patch(
        f"/api/v1/expenses/{expense['id']}",
        json={
            "bank_account_id": account["id"],
            "expected_updated_at": expense["updated_at"],
        },
        headers=auth_headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["bank_account_id"] == account["id"]


# ---------------------------------------------------------------------------------- F-3


def test_manual_transaction_rejects_currency_mismatch(client: TestClient, auth_headers: dict):
    period_id = _create_period(client, auth_headers, 2035, 8)
    account = _create_account(client, auth_headers, "GMD Account", currency="GMD")

    resp = client.post(
        "/api/v1/bank-transactions",
        json={
            "bank_account_id": account["id"],
            "financial_period_id": period_id,
            "transaction_type": "DEPOSIT",
            "amount": "50.00",
            "currency": "USD",
            "transaction_date": "2035-08-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text

    unchanged = client.get(f"/api/v1/bank-accounts/{account['id']}", headers=auth_headers).json()
    assert Decimal(str(unchanged["current_balance"])) == Decimal("0.0000")


def test_transfer_rejects_currency_mismatch_against_either_leg(
    client: TestClient, auth_headers: dict
):
    period_id = _create_period(client, auth_headers, 2035, 9)
    source = _create_account(client, auth_headers, "Source GMD", opening_balance="100.00", currency="GMD")
    destination = _create_account(
        client, auth_headers, "Destination GMD", opening_balance="100.00", currency="GMD"
    )

    resp = client.post(
        "/api/v1/bank-transactions/transfer",
        json={
            "source_bank_account_id": source["id"],
            "destination_bank_account_id": destination["id"],
            "financial_period_id": period_id,
            "amount": "50.00",
            "currency": "USD",
            "transaction_date": "2035-09-01",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422, resp.text

    source_after = client.get(f"/api/v1/bank-accounts/{source['id']}", headers=auth_headers).json()
    destination_after = client.get(
        f"/api/v1/bank-accounts/{destination['id']}", headers=auth_headers
    ).json()
    assert Decimal(str(source_after["current_balance"])) == Decimal("100.0000")
    assert Decimal(str(destination_after["current_balance"])) == Decimal("100.0000")


# ---------------------------------------------------------------------------------- F-4


def test_savings_allocation_bank_transaction_is_separately_audited(
    client: TestClient, auth_headers: dict
):
    period_id = _create_period(client, auth_headers, 2035, 10)
    account = _create_account(client, auth_headers, "Audited Vault")

    savings_item_resp = client.post(
        "/api/v1/savings-items",
        json={
            "financial_period_id": period_id,
            "name": "Manual seed",
            "amount": "300.00",
            "currency": "GMD",
            "date": "2035-10-01",
        },
        headers=auth_headers,
    )
    assert savings_item_resp.status_code == 201, savings_item_resp.text

    alloc_resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "bank_account_id": account["id"],
            "amount": "100.00",
            "transaction_date": "2035-10-02",
        },
        headers=auth_headers,
    )
    assert alloc_resp.status_code == 201, alloc_resp.text
    allocation = alloc_resp.json()
    bank_transaction_id = allocation["bank_transaction_id"]
    assert bank_transaction_id is not None

    audit_resp = client.get(
        "/api/v1/audit-logs?page_size=100", headers=auth_headers
    )
    assert audit_resp.status_code == 200, audit_resp.text
    entries = audit_resp.json()["data"]

    allocation_entries = [
        e for e in entries if e["entity_type"] == "SavingsAllocation" and e["entity_id"] == allocation["id"]
    ]
    assert len(allocation_entries) == 1
    assert allocation_entries[0]["after_state"]["bank_transaction_id"] == bank_transaction_id

    bank_txn_entries = [
        e
        for e in entries
        if e["entity_type"] == "BankTransaction"
        and e["entity_id"] == bank_transaction_id
        and e["related_record_type"] == "BankAccount"
        and e["related_record_id"] == account["id"]
    ]
    assert len(bank_txn_entries) == 1


def test_destination_label_only_allocation_has_no_bank_transaction_audit(
    client: TestClient, auth_headers: dict
):
    """No `account` -> no ledger event -> nothing new to audit for BankTransaction here."""
    period_id = _create_period(client, auth_headers, 2035, 11)
    savings_item_resp = client.post(
        "/api/v1/savings-items",
        json={
            "financial_period_id": period_id,
            "name": "Manual seed",
            "amount": "300.00",
            "currency": "GMD",
            "date": "2035-11-01",
        },
        headers=auth_headers,
    )
    assert savings_item_resp.status_code == 201, savings_item_resp.text

    alloc_resp = client.post(
        "/api/v1/savings-allocations",
        json={
            "financial_period_id": period_id,
            "destination_label": "Emergency Fund",
            "amount": "50.00",
        },
        headers=auth_headers,
    )
    assert alloc_resp.status_code == 201, alloc_resp.text
    allocation = alloc_resp.json()
    assert allocation["bank_transaction_id"] is None

    audit_resp = client.get("/api/v1/audit-logs?page_size=100", headers=auth_headers)
    assert audit_resp.status_code == 200, audit_resp.text
    entries = audit_resp.json()["data"]
    bank_txn_entries = [e for e in entries if e["entity_type"] == "BankTransaction"]
    assert bank_txn_entries == []


# ---------------------------------------------------------------------------------- smaller items


def test_apply_rule_rejects_inactive_savings_distribution_rule(
    client: TestClient, auth_headers: dict
):
    period_id = _create_period(client, auth_headers, 2035, 12)
    savings_item_resp = client.post(
        "/api/v1/savings-items",
        json={
            "financial_period_id": period_id,
            "name": "Manual seed",
            "amount": "300.00",
            "currency": "GMD",
            "date": "2035-12-01",
        },
        headers=auth_headers,
    )
    assert savings_item_resp.status_code == 201, savings_item_resp.text

    rule_resp = client.post(
        "/api/v1/savings-distribution-rules",
        json={
            "name": "Soon Inactive",
            "items": [{"destination_label": "Only", "percentage": "100.00"}],
        },
        headers=auth_headers,
    )
    assert rule_resp.status_code == 201, rule_resp.text
    rule = rule_resp.json()

    deactivate_resp = client.patch(
        f"/api/v1/savings-distribution-rules/{rule['id']}",
        json={"is_active": False, "expected_updated_at": rule["updated_at"]},
        headers=auth_headers,
    )
    assert deactivate_resp.status_code == 200, deactivate_resp.text

    apply_resp = client.post(
        "/api/v1/savings-allocations/apply-rule",
        json={"financial_period_id": period_id, "savings_distribution_rule_id": rule["id"]},
        headers=auth_headers,
    )
    assert apply_resp.status_code == 422, apply_resp.text
