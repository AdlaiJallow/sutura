import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.common.database import get_db
from app.common.deps import get_current_user
from app.common.schemas import Page, paginate_meta
from app.salary.schemas import SalaryCreate, SalaryRead
from app.salary.service import SalaryService
from app.users.models import User

router = APIRouter(prefix="/salaries", tags=["salary"])


@router.get("", response_model=Page[SalaryRead])
def list_salaries(
    financial_period_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[SalaryRead]:
    rows, total = SalaryService(db).list(
        current_user, financial_period_id, page=page, page_size=page_size
    )
    return Page[SalaryRead](
        data=[SalaryRead.model_validate(r) for r in rows], meta=paginate_meta(page, page_size, total)
    )


@router.post("", response_model=SalaryRead, status_code=status.HTTP_201_CREATED)
def create_salary(
    payload: SalaryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SalaryRead:
    salary = SalaryService(db).create(current_user, payload)
    return SalaryRead.model_validate(salary)


@router.get("/{salary_id}", response_model=SalaryRead)
def get_salary(
    salary_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SalaryRead:
    salary = SalaryService(db).get(current_user, salary_id)
    return SalaryRead.model_validate(salary)


@router.delete("/{salary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_salary(
    salary_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    SalaryService(db).delete(current_user, salary_id)
