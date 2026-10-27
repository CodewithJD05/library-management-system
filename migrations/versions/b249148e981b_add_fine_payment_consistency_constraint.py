"""add fine payment consistency constraint

Revision ID: b249148e981b
Revises: 4f4392e295f4
Create Date: 2026-10-27 16:33:55.873715

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b249148e981b'
down_revision: Union[str, Sequence[str], None] = '4f4392e295f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.create_check_constraint(
        "ck_fines_payment_timestamp_consistent",
        "fines",
        "(status = 'unpaid' AND paid_at IS NULL) OR "
        "(status = 'paid' AND paid_at IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_fines_payment_timestamp_consistent",
        "fines",
        type_="check",
    )
