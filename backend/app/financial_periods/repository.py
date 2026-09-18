import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.common.repository_utils import count_query
from app.financial_periods.models import FinancialPeriod, MonthlyFinancialSummary


class FinancialPeriodRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, period: FinancialPeriod) -> FinancialPeriod:
        self.db.add(period)
        self.db.flush()
        return period

    def get_owned(self, user_id: uuid.UUID, period_id: uuid.UUID) -> FinancialPeriod | None:
        stmt = select(FinancialPeriod).where(
            FinancialPeriod.id == period_id, FinancialPeriod.user_id == user_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_year_month(
        self, user_id: uuid.UUID, year: int, month: int
    ) -> FinancialPeriod | None:
        stmt = select(FinancialPeriod).where(
            FinancialPeriod.user_id == user_id,
            FinancialPeriod.year == year,
            FinancialPeriod.month == month,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_periods(
        self,
        user_id: uuid.UUID,
        *,
        year: int | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[FinancialPeriod], int]:
        stmt = select(FinancialPeriod).where(FinancialPeriod.user_id == user_id)
        if year is not None:
            stmt = stmt.where(FinancialPeriod.year == year)
        if status is not None:
            stmt = stmt.where(FinancialPeriod.status == status)
        total = count_query(self.db, stmt)
        stmt = (
            stmt.order_by(FinancialPeriod.year.desc(), FinancialPeriod.month.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list(self.db.execute(stmt).scalars().all())
        return rows, total

    def save(self, period: FinancialPeriod) -> FinancialPeriod:
        self.db.add(period)
        self.db.flush()
        return period

    # --- MonthlyFinancialSummary ---
    def get_current_summary(self, financial_period_id: uuid.UUID) -> MonthlyFinancialSummary | None:
        stmt = select(MonthlyFinancialSummary).where(
            MonthlyFinancialSummary.financial_period_id == financial_period_id,
            MonthlyFinancialSummary.is_current.is_(True),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_version(self, financial_period_id: uuid.UUID) -> int:
        stmt = select(MonthlyFinancialSummary.version).where(
            MonthlyFinancialSummary.financial_period_id == financial_period_id
        ).order_by(MonthlyFinancialSummary.version.desc())
        version = self.db.execute(stmt).scalars().first()
        return version or 0

    def clear_current_flag(self, financial_period_id: uuid.UUID) -> None:
        self.db.execute(
            update(MonthlyFinancialSummary)
            .where(
                MonthlyFinancialSummary.financial_period_id == financial_period_id,
                MonthlyFinancialSummary.is_current.is_(True),
            )
            .values(is_current=False)
        )

    def add_summary(self, summary: MonthlyFinancialSummary) -> MonthlyFinancialSummary:
        self.db.add(summary)
        self.db.flush()
        return summary
