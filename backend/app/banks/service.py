import uuid

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.banks.models import BankAccount
from app.banks.repository import BankAccountRepository
from app.banks.schemas import BankAccountCreate, BankAccountUpdate
from app.common.errors import ConflictError, NotFoundError, ValidationAppError
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

    def update(self, user: User, account_id: uuid.UUID, payload: BankAccountUpdate) -> BankAccount:
        account = self.get(user, account_id)

        data = payload.model_dump(exclude_unset=True, exclude={"expected_updated_at"})
        identifier_provided = "account_identifier" in data
        raw_identifier = data.pop("account_identifier", None)
        if identifier_provided:
            data["account_identifier_last4"] = raw_identifier[-4:] if raw_identifier else None

        if not data:
            raise ValidationAppError("No fields provided to update.")

        before = {
            "account_name": account.account_name,
            "institution_name": account.institution_name,
            "account_type": account.account_type,
            "account_identifier_last4": account.account_identifier_last4,
            "notes": account.notes,
            "is_active": account.is_active,
        }

        rowcount = self.repo.update_owned(user.id, account_id, payload.expected_updated_at, data)
        if rowcount == 0:
            raise ConflictError(
                "This bank account was modified by another request. Reload and try again."
            )

        updated = self.get(user, account_id)
        self.audit.record(
            user_id=user.id,
            entity_type="BankAccount",
            entity_id=updated.id,
            action="UPDATE",
            before_state=before,
            after_state={
                "account_name": updated.account_name,
                "institution_name": updated.institution_name,
                "account_type": updated.account_type,
                "account_identifier_last4": updated.account_identifier_last4,
                "notes": updated.notes,
                "is_active": updated.is_active,
            },
        )
        self.db.commit()
        return updated

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
