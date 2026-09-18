"""Tiny shared repository helper — count-for-pagination. Not a generic base-repository
abstraction on purpose (rule 13: no premature abstraction); each module's repository still
writes its own explicit, readable queries scoped by user_id (D-020)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select


def count_query(db: Session, stmt: Select) -> int:
    return db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
