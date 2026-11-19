"""Add super admin, revocable sessions, member categories, holidays and reservations.

Revision ID: c7f94ab1102e
Revises: b249148e981b
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c7f94ab1102e'
down_revision: Union[str, None] = 'b249148e981b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('staff_users') as batch:
        batch.drop_constraint('ck_staff_users_role', type_='check')
        batch.create_check_constraint('ck_staff_users_role', "role IN ('super_admin', 'admin', 'librarian')")
    op.create_index('uq_staff_one_super_admin', 'staff_users', ['role'], unique=True,
                    postgresql_where=sa.text("role = 'super_admin'"), sqlite_where=sa.text("role = 'super_admin'"))
    with op.batch_alter_table('members') as batch:
        batch.add_column(sa.Column('category', sa.String(20), nullable=False, server_default='student'))
        batch.create_check_constraint('ck_members_category', "category IN ('student', 'faculty')")

    op.create_table('auth_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('staff_user_id', sa.Integer(), sa.ForeignKey('staff_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('refresh_token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('rotation_count', sa.Integer(), nullable=False),
    )
    op.create_index('ix_auth_sessions_staff_user_id', 'auth_sessions', ['staff_user_id'])
    op.create_table('holidays',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('day', sa.Date(), nullable=False, unique=True),
        sa.Column('name', sa.String(150), nullable=False),
    )
    op.create_index('ix_holidays_day', 'holidays', ['day'], unique=True)
    op.create_table('reservations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.id'), nullable=False),
        sa.Column('member_id', sa.Integer(), sa.ForeignKey('members.id'), nullable=False),
        sa.Column('book_copy_id', sa.Integer(), sa.ForeignKey('book_copies.id')),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ready_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('fulfilled_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('waiting','ready','fulfilled','cancelled','expired')", name='ck_reservations_status'),
    )
    op.create_index('ix_reservations_book_id', 'reservations', ['book_id'])
    op.create_index('ix_reservations_member_id', 'reservations', ['member_id'])
    op.create_index('uq_reservations_one_pending_per_member_book', 'reservations', ['member_id', 'book_id'], unique=True,
                    postgresql_where=sa.text("status IN ('waiting','ready')"),
                    sqlite_where=sa.text("status IN ('waiting','ready')"))
    op.create_index('uq_reservations_one_ready_per_copy', 'reservations', ['book_copy_id'], unique=True,
                    postgresql_where=sa.text("status = 'ready'"), sqlite_where=sa.text("status = 'ready'"))
    op.create_table('email_notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_key', sa.String(180), nullable=False, unique=True),
        sa.Column('recipient', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True)),
        sa.Column('last_error', sa.String(500)),
    )


def downgrade() -> None:
    op.drop_table('email_notifications')
    op.drop_index('uq_reservations_one_ready_per_copy', table_name='reservations')
    op.drop_index('uq_reservations_one_pending_per_member_book', table_name='reservations')
    op.drop_index('ix_reservations_member_id', table_name='reservations')
    op.drop_index('ix_reservations_book_id', table_name='reservations')
    op.drop_table('reservations')
    op.drop_index('ix_holidays_day', table_name='holidays')
    op.drop_table('holidays')
    op.drop_index('ix_auth_sessions_staff_user_id', table_name='auth_sessions')
    op.drop_table('auth_sessions')
    with op.batch_alter_table('members') as batch:
        batch.drop_constraint('ck_members_category', type_='check')
        batch.drop_column('category')
    op.drop_index('uq_staff_one_super_admin', table_name='staff_users')
    with op.batch_alter_table('staff_users') as batch:
        batch.drop_constraint('ck_staff_users_role', type_='check')
        batch.create_check_constraint('ck_staff_users_role', "role IN ('admin', 'librarian')")
