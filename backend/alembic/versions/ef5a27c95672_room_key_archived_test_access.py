"""room key, archived, test access

Revision ID: ef5a27c95672
Revises: 1605e26b7870
Create Date: 2026-10-24 22:55:24.101416

"""
import secrets
import string
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ef5a27c95672"
down_revision: Union[str, Sequence[str], None] = "1605e26b7870"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ALPHABET = string.ascii_uppercase + string.digits


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column("tests", sa.Column("room_key", sa.String(), nullable=True))
    op.add_column(
        "tests", sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false())
    )

    # Backfill a unique room key for any tests created before this column existed.
    used: set[str] = set()
    for (test_id,) in conn.execute(sa.text("SELECT id FROM tests")).fetchall():
        key = "".join(secrets.choice(ALPHABET) for _ in range(6))
        while key in used:
            key = "".join(secrets.choice(ALPHABET) for _ in range(6))
        used.add(key)
        conn.execute(sa.text("UPDATE tests SET room_key = :key WHERE id = :id"), {"key": key, "id": test_id})

    op.create_index("ix_tests_room_key", "tests", ["room_key"], unique=True)
    with op.batch_alter_table("tests", schema=None) as batch_op:
        batch_op.alter_column("room_key", existing_type=sa.String(), nullable=False)

    op.create_table(
        "test_access",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("test_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "test_id"),
    )


def downgrade() -> None:
    op.drop_table("test_access")
    op.drop_index("ix_tests_room_key", table_name="tests")
    with op.batch_alter_table("tests", schema=None) as batch_op:
        batch_op.drop_column("archived")
        batch_op.drop_column("room_key")
