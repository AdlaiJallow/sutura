"""drop savings undistributed_total nonneg check

Revision ID: 1b77beeddfa9
Revises: 3eb0672162e8
Create Date: 2026-09-18 18:13:21.699329

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b77beeddfa9'
down_revision: Union[str, None] = '3eb0672162e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_savings_undistributed_nonneg", "savings", type_="check")


def downgrade() -> None:
    op.create_check_constraint(
        "ck_savings_undistributed_nonneg", "savings", "undistributed_total >= 0"
    )
