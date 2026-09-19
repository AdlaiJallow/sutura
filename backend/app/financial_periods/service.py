"""FinancialPeriod service — the first complete vertical slice (spec's central entity, §5).

Owns period create/list/get/close/reopen. Close/reopen assemble the MonthlyFinancialSummary
snapshot by querying sibling modules' persisted rows directly and handing already-fetched
Decimal values to `financial_engine` (never re-implementing the math here, never trusting a
posted total). Every query is scoped by the authenticated user's id (D-020); a period id that
exists but belongs to another user is indistinguishable from a missing one (404).
"""
import calendar
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.allowances.models import Allowance
from app.audit.service import AuditService
from app.common.errors import ConflictError, NotFoundError, ValidationAppError
from app.distribution.models import DistributionCategory, DistributionRule
from app.expenses.models import Expense
from app.financial_engine.distribution_calculator import compute_category_distribution
from app.financial_engine.income_calculator import (
    total_allowances as calc_total_allowances,
)
from app.financial_engine.income_calculator import (
    total_monthly_income as calc_total_monthly_income,
)
from app.financial_engine.income_calculator import (
    total_other_income as calc_total_other_income,
)
from app.financial_engine.income_calculator import total_salary_income as calc_total_salary_income
from app.financial_engine.monthly_summary_calculator import (
    MonthlySummaryInputs,
    build_monthly_summary,
)
from app.financial_engine.rounding import quantize_money
from app.financial_engine.savings_calculator import (
    CategoryRemainderInput,
    automatic_savings as calc_automatic_savings,
    final_savings as calc_final_savings,
    manual_savings_total as calc_manual_savings_total,
)
from app.financial_periods.models import FinancialPeriod, MonthlyFinancialSummary
from app.financial_periods.repository import FinancialPeriodRepository
from app.financial_periods.schemas import FinancialPeriodCreate
from app.income.models import Income
from app.salary.models import Salary
from app.savings.models import Savings, SavingsAllocation, SavingsItem
from app.transactions.models import BankTransaction
from app.users.models import User

ZERO = Decimal("0")


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)
    return start, end


@dataclass(frozen=True)
class IncomeTotals:
    """Output of `_compute_income_totals` — the salary/allowance/other-income figures shared by
    both `_compute_summary` (the closed-form MonthlyFinancialSummary) and `get_distribution_view`
    (the per-category read view), so the two never run these queries/formulas independently."""

    net_salary: Decimal
    allowances_total: Decimal
    other_income_total: Decimal
    salary_income: Decimal
    monthly_income: Decimal


@dataclass(frozen=True)
class CategoryDistributionDetail:
    """One category's full computed detail for `GET /distributions/{period_id}` (spec §12/§26).
    Wraps `financial_engine.distribution_calculator.compute_category_distribution` with the
    category's own persisted metadata (name/percentage/flags) — the single place both the
    summary's automatic-savings input and the read-only distribution view are derived from."""

    id: uuid.UUID
    name: str
    percentage: Decimal
    contributes_to_automatic_savings: bool
    is_unallocated_bucket: bool
    allocation: Decimal
    used: Decimal
    remaining: Decimal
    is_overspent: bool


@dataclass(frozen=True)
class DistributionViewResult:
    financial_period_id: uuid.UUID
    distribution_rule_id: uuid.UUID | None
    distribution_rule_name: str | None
    total_monthly_income: Decimal
    categories: list[CategoryDistributionDetail]
    total_allocation: Decimal
    total_used: Decimal
    total_remaining: Decimal


class FinancialPeriodService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = FinancialPeriodRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ CRUD

    def create_period(self, user: User, payload: FinancialPeriodCreate) -> FinancialPeriod:
        if self.repo.get_by_year_month(user.id, payload.year, payload.month):
            raise ConflictError(
                f"A financial period for {payload.year}-{payload.month:02d} already exists."
            )
        start, end = _month_bounds(payload.year, payload.month)
        period = FinancialPeriod(
            user_id=user.id,
            year=payload.year,
            month=payload.month,
            start_date=start,
            end_date=end,
            status="OPEN",
            base_currency=user.default_currency,
        )
        self.repo.create(period)
        self.audit.record(
            user_id=user.id,
            entity_type="FinancialPeriod",
            entity_id=period.id,
            action="CREATE",
            after_state={"year": period.year, "month": period.month},
        )
        self.db.commit()
        # NOTE: RecurringTemplate materialization (D-003) is a Celery job wired up in Phase 3
        # once salary/allowances/income/expenses have real create paths to generate into.
        return period

    def get_period(self, user: User, period_id: uuid.UUID) -> FinancialPeriod:
        period = self.repo.get_owned(user.id, period_id)
        if period is None:
            raise NotFoundError("Financial period not found.")
        return period

    def get_or_create_current(self, user: User) -> FinancialPeriod:
        today = date.today()
        existing = self.repo.get_by_year_month(user.id, today.year, today.month)
        if existing is not None:
            return existing
        return self.create_period(
            user, FinancialPeriodCreate(year=today.year, month=today.month)
        )

    def list_periods(
        self,
        user: User,
        *,
        year: int | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[FinancialPeriod], int]:
        return self.repo.list_periods(user.id, year=year, status=status, page=page, page_size=page_size)

    def patch_period(self, user: User, period_id: uuid.UUID, notes: str | None) -> FinancialPeriod:
        period = self.get_period(user, period_id)
        if period.status == "CLOSED":
            raise ConflictError("Cannot edit a closed financial period.")
        # FinancialPeriod has no `notes` column today (not in erd.md) — accepted as a no-op
        # placeholder for the PATCH contract until a real editable field is added.
        self.repo.save(period)
        self.db.commit()
        return period

    def select_distribution_rule(
        self, user: User, period_id: uuid.UUID, distribution_rule_id: uuid.UUID
    ) -> FinancialPeriod:
        period = self.get_period(user, period_id)
        if period.status == "CLOSED":
            raise ConflictError("Cannot change the distribution rule of a closed period.")
        rule = self.db.execute(
            select(DistributionRule).where(
                DistributionRule.id == distribution_rule_id,
                DistributionRule.user_id == user.id,
                DistributionRule.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if rule is None:
            raise NotFoundError("Distribution rule not found.")
        before = {"distribution_rule_id": str(period.distribution_rule_id) if period.distribution_rule_id else None}
        period.distribution_rule_id = rule.id
        self.repo.save(period)
        self.audit.record(
            user_id=user.id,
            entity_type="FinancialPeriod",
            entity_id=period.id,
            action="UPDATE",
            before_state=before,
            after_state={"distribution_rule_id": str(rule.id)},
        )
        self.db.commit()
        return period

    # ------------------------------------------------------------------ summary computation

    def _compute_income_totals(self, user: User, period: FinancialPeriod) -> IncomeTotals:
        """Net salary + allowances + other income -> Total Monthly Income (spec §26). Shared by
        `_compute_summary` and `get_distribution_view` so both read the exact same figures from
        the exact same queries — never re-derived independently."""
        db = self.db

        salary_row = db.execute(
            select(Salary).where(
                Salary.user_id == user.id,
                Salary.financial_period_id == period.id,
                Salary.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        net_salary = Decimal(salary_row.net_amount) if salary_row else ZERO

        allowance_amounts = db.execute(
            select(Allowance.amount).where(
                Allowance.user_id == user.id,
                Allowance.financial_period_id == period.id,
                Allowance.deleted_at.is_(None),
            )
        ).scalars().all()
        allowances_total = calc_total_allowances(Decimal(a) for a in allowance_amounts)

        income_amounts = db.execute(
            select(Income.amount).where(
                Income.user_id == user.id,
                Income.financial_period_id == period.id,
                Income.deleted_at.is_(None),
            )
        ).scalars().all()
        other_income_total = calc_total_other_income(Decimal(a) for a in income_amounts)

        salary_income = calc_total_salary_income(net_salary, allowances_total)
        monthly_income = calc_total_monthly_income(salary_income, other_income_total)

        return IncomeTotals(
            net_salary=net_salary,
            allowances_total=allowances_total,
            other_income_total=other_income_total,
            salary_income=salary_income,
            monthly_income=monthly_income,
        )

    def _gather_category_details(
        self, user_id: uuid.UUID, period: FinancialPeriod, total_monthly_income: Decimal
    ) -> list[CategoryDistributionDetail]:
        """The one query+math implementation for per-category allocation/used/remaining
        (spec §12/§26), routed through `financial_engine.distribution_calculator
        .compute_category_distribution` so `is_overspent` is never computed ad hoc. Used by both
        `_gather_category_remainders` (automatic-savings input) and `get_distribution_view`
        (the read-only `/distributions/{period_id}` endpoint)."""
        if period.distribution_rule_id is None:
            return []

        categories = list(
            self.db.execute(
                select(DistributionCategory)
                .where(DistributionCategory.distribution_rule_id == period.distribution_rule_id)
                .order_by(DistributionCategory.display_order, DistributionCategory.name)
            ).scalars()
        )

        details: list[CategoryDistributionDetail] = []
        for cat in categories:
            used_amounts = self.db.execute(
                select(Expense.amount).where(
                    Expense.user_id == user_id,
                    Expense.financial_period_id == period.id,
                    Expense.distribution_category_id == cat.id,
                    Expense.deleted_at.is_(None),
                )
            ).scalars().all()
            result = compute_category_distribution(
                category_id=cat.id,
                total_monthly_income=total_monthly_income,
                percentage=Decimal(cat.percentage),
                item_amounts=(Decimal(a) for a in used_amounts),
                contributes_to_automatic_savings=cat.contributes_to_automatic_savings,
            )
            details.append(
                CategoryDistributionDetail(
                    id=cat.id,
                    name=cat.name,
                    percentage=Decimal(cat.percentage),
                    contributes_to_automatic_savings=cat.contributes_to_automatic_savings,
                    is_unallocated_bucket=cat.is_unallocated_bucket,
                    allocation=result.allocation,
                    used=result.used,
                    remaining=result.remaining,
                    is_overspent=result.is_overspent,
                )
            )
        return details

    def _gather_category_remainders(
        self, user_id: uuid.UUID, period: FinancialPeriod, total_monthly_income: Decimal
    ) -> tuple[list[CategoryRemainderInput], Decimal]:
        """Returns (per-category remainder inputs, total_planned_savings) where
        total_planned_savings is the sum of allocations for categories flagged as contributing
        to automatic savings (the budget set aside, not yet the unused remainder). Thin
        derivation from `_gather_category_details` — same signature/behavior as before, but no
        longer a second query+math implementation."""
        details = self._gather_category_details(user_id, period, total_monthly_income)
        remainders = [
            CategoryRemainderInput(
                remaining=d.remaining,
                contributes_to_automatic_savings=d.contributes_to_automatic_savings,
            )
            for d in details
        ]
        total_planned_savings = sum(
            (d.allocation for d in details if d.contributes_to_automatic_savings), ZERO
        )
        return remainders, total_planned_savings

    def get_distribution_view(self, user: User, period_id: uuid.UUID) -> DistributionViewResult:
        """Read-only computed view for `GET /distributions/{period_id}` (docs/api-contract.md
        §9): per-category allocation/used/remaining/is_overspent plus period totals, server
        -computed and never stored redundantly. No commit, no audit entry — this reads persisted
        rows and derives numbers, it never mutates anything.

        A period with no distribution rule selected yet is a normal state (a brand-new period),
        not an error: this returns 200 with `distribution_rule_id/name = null`, `categories = []`
        and zeroed totals, rather than forcing every caller to special-case a 404."""
        period = self.get_period(user, period_id)
        income = self._compute_income_totals(user, period)

        rule_name: str | None = None
        if period.distribution_rule_id is not None:
            rule_name = self.db.execute(
                select(DistributionRule.name).where(
                    DistributionRule.id == period.distribution_rule_id
                )
            ).scalar_one_or_none()

        categories = self._gather_category_details(user.id, period, income.monthly_income)
        total_allocation = quantize_money(sum((c.allocation for c in categories), ZERO))
        total_used = quantize_money(sum((c.used for c in categories), ZERO))
        total_remaining = quantize_money(sum((c.remaining for c in categories), ZERO))

        return DistributionViewResult(
            financial_period_id=period.id,
            distribution_rule_id=period.distribution_rule_id,
            distribution_rule_name=rule_name,
            total_monthly_income=income.monthly_income,
            categories=categories,
            total_allocation=total_allocation,
            total_used=total_used,
            total_remaining=total_remaining,
        )

    def _compute_summary(self, user: User, period: FinancialPeriod) -> MonthlySummaryInputs:
        db = self.db

        income = self._compute_income_totals(user, period)
        net_salary = income.net_salary
        allowances_total = income.allowances_total
        other_income_total = income.other_income_total
        monthly_income = income.monthly_income

        expense_amounts = db.execute(
            select(Expense.amount).where(
                Expense.user_id == user.id,
                Expense.financial_period_id == period.id,
                Expense.deleted_at.is_(None),
            )
        ).scalars().all()
        expenses_total = sum((Decimal(a) for a in expense_amounts), ZERO)

        remainders, total_planned_savings = self._gather_category_remainders(
            user.id, period, monthly_income
        )
        automatic = calc_automatic_savings(remainders)

        manual_amounts = db.execute(
            select(SavingsItem.amount).where(
                SavingsItem.user_id == user.id,
                SavingsItem.financial_period_id == period.id,
                SavingsItem.deleted_at.is_(None),
            )
        ).scalars().all()
        manual_total = calc_manual_savings_total(Decimal(a) for a in manual_amounts)

        final = calc_final_savings(automatic, manual_total)

        savings_row = db.execute(
            select(Savings).where(
                Savings.financial_period_id == period.id, Savings.user_id == user.id
            )
        ).scalar_one_or_none()
        distributed_total = ZERO
        if savings_row is not None:
            allocated_amounts = db.execute(
                select(SavingsAllocation.amount).where(
                    SavingsAllocation.savings_id == savings_row.id,
                    SavingsAllocation.user_id == user.id,
                )
            ).scalars().all()
            distributed_total = sum((Decimal(a) for a in allocated_amounts), ZERO)

        deposit_amounts = db.execute(
            select(BankTransaction.amount).where(
                BankTransaction.user_id == user.id,
                BankTransaction.financial_period_id == period.id,
                BankTransaction.transaction_type == "DEPOSIT",
            )
        ).scalars().all()
        total_bank_deposits = sum((Decimal(a) for a in deposit_amounts), ZERO)

        # Upsert the Savings cache row (D-012) so `/savings/{period_id}` stays in sync.
        now = datetime.now(timezone.utc)
        if savings_row is None:
            savings_row = Savings(
                user_id=user.id,
                financial_period_id=period.id,
                automatic_savings_computed=automatic,
                manual_savings_total=manual_total,
                final_savings_total=final,
                distributed_total=distributed_total,
                undistributed_total=final - distributed_total,
                last_calculated_at=now,
            )
        else:
            savings_row.automatic_savings_computed = automatic
            savings_row.manual_savings_total = manual_total
            savings_row.final_savings_total = final
            savings_row.distributed_total = distributed_total
            savings_row.undistributed_total = final - distributed_total
            savings_row.last_calculated_at = now
        db.add(savings_row)
        db.flush()

        return MonthlySummaryInputs(
            net_salary=net_salary,
            total_allowances=allowances_total,
            total_other_income=other_income_total,
            total_expenses=expenses_total,
            total_planned_savings=total_planned_savings,
            automatic_savings=automatic,
            manual_savings=manual_total,
            total_bank_deposits=total_bank_deposits,
            distributed_savings=distributed_total,
        )

    def _write_summary_version(
        self, user: User, period: FinancialPeriod, triggered_by: str
    ) -> MonthlyFinancialSummary:
        inputs = self._compute_summary(user, period)
        result = build_monthly_summary(inputs)

        self.repo.clear_current_flag(period.id)
        next_version = self.repo.get_latest_version(period.id) + 1
        summary = MonthlyFinancialSummary(
            user_id=user.id,
            financial_period_id=period.id,
            version=next_version,
            is_current=True,
            total_salary_income=result.total_salary_income,
            total_allowances=result.total_allowances,
            total_other_income=result.total_other_income,
            total_monthly_income=result.total_monthly_income,
            total_expenses=result.total_expenses,
            total_planned_savings=result.total_planned_savings,
            automatic_savings=result.automatic_savings,
            manual_savings=result.manual_savings,
            final_savings=result.final_savings,
            total_bank_deposits=result.total_bank_deposits,
            undistributed_savings=result.undistributed_savings,
            triggered_by=triggered_by,
            calculated_at=datetime.now(timezone.utc),
        )
        self.repo.add_summary(summary)
        return summary

    # ------------------------------------------------------------------ close / reopen

    def close_period(self, user: User, period_id: uuid.UUID) -> FinancialPeriod:
        period = self.get_period(user, period_id)
        if period.status == "CLOSED":
            raise ConflictError("Financial period is already closed.")

        summary = self._write_summary_version(user, period, triggered_by="CLOSE")

        period.status = "CLOSED"
        period.closed_at = datetime.now(timezone.utc)
        period.closed_by = user.id
        self.repo.save(period)

        self.audit.record(
            user_id=user.id,
            entity_type="FinancialPeriod",
            entity_id=period.id,
            action="CLOSE",
            after_state={"summary_version": summary.version, "status": "CLOSED"},
            related_record_type="MonthlyFinancialSummary",
            related_record_id=summary.id,
        )
        self.db.commit()
        return period

    def reopen_period(self, user: User, period_id: uuid.UUID, reason: str) -> FinancialPeriod:
        period = self.get_period(user, period_id)
        if period.status != "CLOSED":
            raise ConflictError("Only a closed financial period can be reopened.")
        if not reason or not reason.strip():
            raise ValidationAppError("A reason is required to reopen a financial period.")

        previous_summary = self.repo.get_current_summary(period.id)

        period.status = "OPEN"
        period.reopened_count += 1
        period.last_reopened_at = datetime.now(timezone.utc)
        period.closed_at = None
        period.closed_by = None
        self.repo.save(period)

        self.audit.record(
            user_id=user.id,
            entity_type="FinancialPeriod",
            entity_id=period.id,
            action="REOPEN",
            before_state={
                "status": "CLOSED",
                "summary_version": previous_summary.version if previous_summary else None,
                "reason": reason,
            },
            after_state={"status": "OPEN", "reopened_count": period.reopened_count},
            related_record_type="MonthlyFinancialSummary",
            related_record_id=previous_summary.id if previous_summary else None,
        )
        self.db.commit()
        return period

    def get_summary(self, user: User, period_id: uuid.UUID) -> MonthlyFinancialSummary:
        period = self.get_period(user, period_id)
        if period.status == "OPEN":
            # Live-computed, not persisted, so an open period's summary is always fresh but
            # never creates a phantom "version" for a period that hasn't been closed yet.
            inputs = self._compute_summary(user, period)
            self.db.commit()  # persists the recalculated Savings cache row (D-012)
            result = build_monthly_summary(inputs)
            return MonthlyFinancialSummary(
                id=uuid.uuid4(),
                user_id=user.id,
                financial_period_id=period.id,
                version=0,
                is_current=True,
                total_salary_income=result.total_salary_income,
                total_allowances=result.total_allowances,
                total_other_income=result.total_other_income,
                total_monthly_income=result.total_monthly_income,
                total_expenses=result.total_expenses,
                total_planned_savings=result.total_planned_savings,
                automatic_savings=result.automatic_savings,
                manual_savings=result.manual_savings,
                final_savings=result.final_savings,
                total_bank_deposits=result.total_bank_deposits,
                undistributed_savings=result.undistributed_savings,
                triggered_by="MANUAL_REFRESH",
                calculated_at=datetime.now(timezone.utc),
            )
        summary = self.repo.get_current_summary(period.id)
        if summary is None:
            raise NotFoundError("No summary has been calculated for this period yet.")
        return summary
