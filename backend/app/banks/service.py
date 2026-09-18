import uuid

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.banks.models import BankAccount
from app.banks.repository import BankAccountRepository
from app.banks.schemas import BankAccountCreate
from app.common.errors import NotFoundError
from app.users.models import User


class BankAccountService:
    """Account identifiers are never stored or returned in plaintext (§17/§34): only the last
    4 characters are persisted for masked display; full encryption-at-rest of the identifier is
    a Phase 4 (Accounts) concern once real bank-linking is built — today the column exists and
    is never populated with plaintext by this service."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = BankAccountRepository(db)
        self.audit = AuditService(db)

    def create(self, user: User, payload: BankAccountCreate) -> BankAccount:
        last4 = payload.account_identifier[-4:] if payload.account_identifier else None
        account = BankAccount(
            user_id=user.id,
            account_name=payload.account_name,
            institution_name=payload.institution_name,
            account_type=payload.account_type,
            account_identifier_last4=last4,
            currency=payload.currency.upper(),
            opening_balance=payload.opening_balance,
            current_balance=payload.opening_balance,
        )
        self.repo.create(account)
        self.audit.record(
            user_id=user.id,
            entity_type="BankAccount",
            entity_id=account.id,
            action="CREATE",
            after_state={"account_name": account.account_name},
        )
        self.db.commit()
        return account

    def get(self, user: User, account_id: uuid.UUID) -> BankAccount:
        account = self.repo.get_owned(user.id, account_id)
        if account is None:
            raise NotFoundError("Bank account not found.")
        return account

    def list(
        self, user: User, *, is_active: bool | None, page: int, page_size: int
    ) -> tuple[list[BankAccount], int]:
        return self.repo.list(user.id, is_active=is_active, page=page, page_size=page_size)

    def deactivate(self, user: User, account_id: uuid.UUID) -> None:
        account = self.get(user, account_id)
        account.is_active = False
        self.repo.save(account)
        self.audit.record(
            user_id=user.id,
            entity_type="BankAccount",
            entity_id=account.id,
            action="UPDATE",
            after_state={"is_active": False},
        )
        self.db.commit()
