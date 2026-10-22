"""prevent duplicate active borrowings

Revision ID: 3c498110ab10
Revises: 50baa62fd6c0
Create Date: 2026-10-22 17:05:07.070943

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c498110ab10'
down_revision: Union[str, Sequence[str], None] = '50baa62fd6c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.create_index(
        "uq_borrowings_active_book",
        "borrowings",
        ["book_id"],
        unique=True,
        postgresql_where=sa.text("returned_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_borrowings_active_book",
        table_name="borrowings",
    )
