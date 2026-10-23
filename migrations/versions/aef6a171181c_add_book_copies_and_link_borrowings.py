
"""add book copies and link borrowings

Revision ID: aef6a171181c
Revises: 3c498110ab10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "aef6a171181c"
down_revision: Union[str, Sequence[str], None] = "3c498110ab10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the physical book copies table.
    op.create_table(
        "book_copies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_book_copies_id",
        "book_copies",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_book_copies_book_id",
        "book_copies",
        ["book_id"],
        unique=False,
    )
    op.create_index(
        "ix_book_copies_barcode",
        "book_copies",
        ["barcode"],
        unique=True,
    )

    # 2. Create one initial physical copy for every existing book.
    op.execute(
        sa.text("""
            INSERT INTO book_copies (book_id, barcode, status)
            SELECT id, 'LEGACY-' || CAST(id AS VARCHAR), 'available'
            FROM books
        """)
    )

    # 3. Add the new borrowing reference temporarily as nullable.
    op.add_column(
        "borrowings",
        sa.Column("book_copy_id", sa.Integer(), nullable=True),
    )

    # 4. Preserve borrowing history by linking each borrowing
    # to the initial copy of its original catalogue book.
    op.execute(
        sa.text("""
            UPDATE borrowings AS b
            SET book_copy_id = bc.id
            FROM book_copies AS bc
            WHERE bc.book_id = b.book_id
        """)
    )

    # 5. Require every borrowing to reference a physical copy.
    op.alter_column(
        "borrowings",
        "book_copy_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_foreign_key(
        "fk_borrowings_book_copy_id_book_copies",
        "borrowings",
        "book_copies",
        ["book_copy_id"],
        ["id"],
    )

    op.create_index(
        "ix_borrowings_book_copy_id",
        "borrowings",
        ["book_copy_id"],
        unique=False,
    )

    # 6. Replace the old active-book constraint with one per copy.
    op.drop_index(
        "uq_borrowings_active_book",
        table_name="borrowings",
    )

    op.create_index(
        "uq_borrowings_active_book_copy",
        "borrowings",
        ["book_copy_id"],
        unique=True,
        postgresql_where=sa.text("returned_at IS NULL"),
    )

    # 7. Remove the old catalogue-level borrowing reference.
    op.drop_constraint(
        "borrowings_book_id_fkey",
        "borrowings",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_borrowings_book_id",
        table_name="borrowings",
    )
    op.drop_column("borrowings", "book_id")


def downgrade() -> None:
    # Restore the original catalogue reference before removing
    # the physical-copy relationship.
    op.add_column(
        "borrowings",
        sa.Column("book_id", sa.Integer(), nullable=True),
    )

    op.execute(
        sa.text("""
            UPDATE borrowings AS b
            SET book_id = bc.book_id
            FROM book_copies AS bc
            WHERE bc.id = b.book_copy_id
        """)
    )

    op.alter_column(
        "borrowings",
        "book_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_foreign_key(
        "borrowings_book_id_fkey",
        "borrowings",
        "books",
        ["book_id"],
        ["id"],
    )
    op.create_index(
        "ix_borrowings_book_id",
        "borrowings",
        ["book_id"],
        unique=False,
    )

    op.drop_index(
        "uq_borrowings_active_book_copy",
        table_name="borrowings",
    )
    op.drop_index(
        "ix_borrowings_book_copy_id",
        table_name="borrowings",
    )
    op.drop_constraint(
        "fk_borrowings_book_copy_id_book_copies",
        "borrowings",
        type_="foreignkey",
    )
    op.drop_column("borrowings", "book_copy_id")

    # This may fail if different copies of the same book are
    # currently borrowed simultaneously.
    op.create_index(
        "uq_borrowings_active_book",
        "borrowings",
        ["book_id"],
        unique=True,
        postgresql_where=sa.text("returned_at IS NULL"),
    )

    op.drop_index(
        "ix_book_copies_barcode",
        table_name="book_copies",
    )
    op.drop_index(
        "ix_book_copies_book_id",
        table_name="book_copies",
    )
    op.drop_index(
        "ix_book_copies_id",
        table_name="book_copies",
    )
    op.drop_table("book_copies")
