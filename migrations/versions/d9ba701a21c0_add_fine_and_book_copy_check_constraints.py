"""add fine and book copy check constraints

Revision ID: d9ba701a21c0
Revises: a6f400c198c8
Create Date: 2026-10-26 18:27:20.625660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9ba701a21c0'
down_revision: Union[str, Sequence[str], None] = 'a6f400c198c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.create_check_constraint(
        "ck_fines_amount_nonnegative",
        "fines",
        "amount >= 0",
    )

    op.create_check_constraint(
        "ck_fines_daily_rate_positive",
        "fines",
        "daily_rate > 0",
    )

    op.create_check_constraint(
        "ck_fines_status_valid",
        "fines",
        "status IN ('unpaid', 'paid')",
    )

    op.create_check_constraint(
        "ck_book_copies_status_valid",
        "book_copies",
        "status IN ('available', 'borrowed')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_book_copies_status_valid",
        "book_copies",
        type_="check",
    )

    op.drop_constraint(
        "ck_fines_status_valid",
        "fines",
        type_="check",
    )

    op.drop_constraint(
        "ck_fines_daily_rate_positive",
        "fines",
        type_="check",
    )

    op.drop_constraint(
        "ck_fines_amount_nonnegative",
        "fines",
        type_="check",
    )
