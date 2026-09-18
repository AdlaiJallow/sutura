import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.banks.repository import BankAccountRepository
from app.common.errors import ConflictError, NotFoundError, ValidationAppError
from app.financial_periods.models import FinancialPeriod
from app.financial_periods.repository import FinancialPeriodRepository
from app.transactions.models import BankTransaction
from app.transactions.repository import BankTransactionRepository
from app.transactions.schemas import BankTransactionCreate, BankTransferCreate
from app.users.models import User

SIGN_BY_TYPE = {
    "DEPOSIT": 1,
    "TRANSFER_IN": 1,
    "WITHDRAWAL": -1,
    "TRANSFER_OUT": -1,
    "ADJUSTMENT": 1,
}


class BankTransactionService:
    """Append-only ledger (D-016): no PATCH/DELETE. `current_balance` on the account is
    recalculated transactionally on every insert (D-011)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = BankTransactionRepository(db)
        self.accounts = BankAccountRepository(db)
        self.periods = FinancialPeriodRepository(db)
        self.audit = AuditService(db)

    def _ensure_period_open(self, user: User, financial_period_id: uuid.UUID) -> FinancialPeriod:
        """Same closed-period guard convention used by every other module (e.g.
        `app.expenses.service.ExpenseService._ensure_period_open`). This was missing here in
        Phase 3 — bank transactions could previously be posted into a closed period's financial
        history, contradicting D-004/spec §37."""
        period = self.periods.get_owned(user.id, financial_period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        if period.status == "CLOSED":
            raise ConflictError("Cannot modify records in a closed financial period.")
        return period

    def create(self, user: User, payload: BankTransactionCreate) -> BankTransaction:
        if payload.transaction_type not in ("DEPOSIT", "WITHDRAWAL", "ADJUSTMENT"):
            raise ValidationAppError(
                "transaction_type must be DEPOSIT, WITHDRAWAL, or ADJUSTMENT "
                "(transfers use POST /bank-transactions/transfer)."
            )
        # Locked (not `get_owned`) from the start (D-025/F-1): this same row is read-modified
        # for `current_balance` below, and the lock must be held for the whole
        # read-check-insert-update sequence to close the lost-update race.
        account = self.accounts.lock_owned(user.id, payload.bank_account_id)
        if account is None:
            raise NotFoundError("Bank account not found.")
        if not account.is_active:
            raise ValidationAppError(
                "Cannot post a transaction to an inactive bank account."
            )
        self._ensure_period_open(user, payload.financial_period_id)

        # F-3: currency is derived from/validated against the account, never trusted as an
        # independent client-supplied field — same principle already applied correctly in
        # SavingsAllocationService.create (which derives currency from the account entirely).
        currency = payload.currency.upper()
        if currency != account.currency:
            raise ValidationAppError(
                f"Transaction currency ({currency}) does not match the bank account's "
                f"currency ({account.currency})."
            )

        txn = BankTransaction(
            user_id=user.id,
            bank_account_id=payload.bank_account_id,
            financial_period_id=payload.financial_period_id,
            transaction_type=payload.transaction_type,
            amount=payload.amount,
            currency=currency,
            transaction_date=payload.transaction_date,
            description=payload.description,
            related_record_type="MANUAL",
        )
        self.repo.create(txn)

        sign = SIGN_BY_TYPE[payload.transaction_type]
        account.current_balance = Decimal(account.current_balance) + sign * Decimal(payload.amount)
        self.accounts.save(account)

        self.audit.record(
            user_id=user.id,
            entity_type="BankTransaction",
            entity_id=txn.id,
            action="CREATE",
            after_state={"amount": str(txn.amount), "transaction_type": txn.transaction_type},
            related_record_type="BankAccount",
            related_record_id=account.id,
        )
        self.db.commit()
        return txn

    def transfer(
        self, user: User, payload: BankTransferCreate
    ) -> tuple[BankTransaction, BankTransaction]:
        """Moves money between two of the *same user's* accounts atomically: one TRANSFER_OUT
        row on the source, one TRANSFER_IN row on the destination, sharing a `transfer_pair_id`,
        both balances updated in the same DB transaction (D-011).

        Ownership is checked independently for both accounts via `lock_owned` (D-020) — a source
        or destination id belonging to another user is 404, identical to a genuinely missing id,
        never 403. A single audit entry is written (on the TRANSFER_OUT leg, cross-referencing
        the destination account) rather than two — one logical operation, one audit record,
        with both resulting transaction ids and the shared `transfer_pair_id` in `after_state`
        giving full traceability of both legs from that one entry.

        Lock ordering (D-025/F-1): both accounts are locked `SELECT ... FOR UPDATE` in a
        consistent order determined by sorting the two account ids themselves (not by
        source/destination role) *before* either row is fetched. Two transfers running in
        opposite directions between the same pair of accounts therefore always attempt to
        acquire the same first lock, so the second transaction simply waits instead of the two
        deadlocking on each other by locking in reverse order.
        """
        if payload.source_bank_account_id == payload.destination_bank_account_id:
            raise ValidationAppError("Cannot transfer to the same bank account.")

        self._ensure_period_open(user, payload.financial_period_id)

        ordered_ids = sorted(
            (payload.source_bank_account_id, payload.destination_bank_account_id)
        )
        locked_accounts = {}
        for account_id in ordered_ids:
            locked = self.accounts.lock_owned(user.id, account_id)
            if locked is None:
                raise NotFoundError("Bank account not found.")
            locked_accounts[account_id] = locked

        source = locked_accounts[payload.source_bank_account_id]
        destination = locked_accounts[payload.destination_bank_account_id]

        if not source.is_active:
            raise ValidationAppError("Cannot transfer from an inactive bank account.")
        if not destination.is_active:
            raise ValidationAppError("Cannot transfer to an inactive bank account.")

        transfer_pair_id = uuid.uuid4()
        amount = Decimal(payload.amount)
        currency = payload.currency.upper()

        # F-3: validate the client-supplied currency against both legs' actual account
        # currencies rather than trusting it — a transfer moves the same numeric amount to both
        # legs, so it must actually match both accounts' currency, not just be well-formed.
        if currency != source.currency:
            raise ValidationAppError(
                f"Transaction currency ({currency}) does not match the source bank account's "
                f"currency ({source.currency})."
            )
        if currency != destination.currency:
            raise ValidationAppError(
                f"Transaction currency ({currency}) does not match the destination bank "
                f"account's currency ({destination.currency})."
            )

        out_txn = BankTransaction(
            user_id=user.id,
            bank_account_id=source.id,
            financial_period_id=payload.financial_period_id,
            transaction_type="TRANSFER_OUT",
            amount=amount,
            currency=currency,
            transaction_date=payload.transaction_date,
            description=payload.description,
            related_record_type="TRANSFER",
            transfer_pair_id=transfer_pair_id,
        )
        self.repo.create(out_txn)

        in_txn = BankTransaction(
            user_id=user.id,
            bank_account_id=destination.id,
            financial_period_id=payload.financial_period_id,
            transaction_type="TRANSFER_IN",
            amount=amount,
            currency=currency,
            transaction_date=payload.transaction_date,
            description=payload.description,
            related_record_type="TRANSFER",
            transfer_pair_id=transfer_pair_id,
        )
        self.repo.create(in_txn)

        source.current_balance = Decimal(source.current_balance) - amount
        destination.current_balance = Decimal(destination.current_balance) + amount
        self.accounts.save(source)
        self.accounts.save(destination)

        self.audit.record(
            user_id=user.id,
            entity_type="BankTransaction",
            entity_id=out_txn.id,
            action="TRANSFER",
            after_state={
                "amount": str(amount),
                "currency": currency,
                "source_bank_account_id": str(source.id),
                "destination_bank_account_id": str(destination.id),
                "transfer_pair_id": str(transfer_pair_id),
                "transfer_in_id": str(in_txn.id),
            },
            related_record_type="BankAccount",
            related_record_id=destination.id,
        )
        self.db.commit()
        return out_txn, in_txn

    def get(self, user: User, txn_id: uuid.UUID) -> BankTransaction:
        txn = self.repo.get_owned(user.id, txn_id)
        if txn is None:
            raise NotFoundError("Bank transaction not found.")
        return txn

    def list(
        self,
        user: User,
        *,
        bank_account_id: uuid.UUID | None,
        financial_period_id: uuid.UUID | None,
        transaction_type: str | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[BankTransaction], int]:
        return self.repo.list(
            user.id,
            bank_account_id=bank_account_id,
            financial_period_id=financial_period_id,
            transaction_type=transaction_type,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
