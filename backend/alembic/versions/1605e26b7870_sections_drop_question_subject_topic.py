"""sections, drop question subject/topic

Revision ID: 1605e26b7870
Revises: e71241f1920b
Create Date: 2026-10-24 15:49:33.726124

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1605e26b7870"
down_revision: Union[str, Sequence[str], None] = "e71241f1920b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    op.create_table(
        "test_sections",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("test_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("duration_mins", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # One default section per existing test, carrying over its old duration_mins,
    # so existing tests and their questions survive the migration.
    for test_id, duration_mins in conn.execute(sa.text("SELECT id, duration_mins FROM tests")).fetchall():
        conn.execute(
            sa.text(
                "INSERT INTO test_sections (id, test_id, title, position, duration_mins) "
                "VALUES (:id, :test_id, 'Section 1', 0, :duration_mins)"
            ),
            {"id": str(uuid.uuid4()), "test_id": test_id, "duration_mins": duration_mins},
        )

    # Recreate test_questions pointing at sections instead of tests directly.
    # Done via raw SQL rather than batch_alter_table since the primary key
    # itself is changing (test_id, question_id) -> (section_id, question_id).
    op.execute(
        """
        CREATE TABLE test_questions_new (
            section_id VARCHAR NOT NULL REFERENCES test_sections(id) ON DELETE CASCADE,
            question_id VARCHAR NOT NULL REFERENCES questions(id),
            position INTEGER NOT NULL,
            PRIMARY KEY (section_id, question_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO test_questions_new (section_id, question_id, position)
        SELECT ts.id, tq.question_id, tq.position
        FROM test_questions tq
        JOIN test_sections ts ON ts.test_id = tq.test_id
        """
    )
    op.execute("DROP TABLE test_questions")
    op.execute("ALTER TABLE test_questions_new RENAME TO test_questions")

    with op.batch_alter_table("tests", schema=None) as batch_op:
        batch_op.drop_column("duration_mins")

    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.drop_index("questions_subject_topic_idx")
        batch_op.drop_column("topic")
        batch_op.drop_column("subject")


def downgrade() -> None:
    """Best-effort inverse: collapses each test back to its first section's duration."""
    conn = op.get_bind()

    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("subject", sa.VARCHAR(), nullable=False, server_default="General"))
        batch_op.add_column(sa.Column("topic", sa.VARCHAR(), nullable=False, server_default="General"))
        batch_op.create_index("questions_subject_topic_idx", ["subject", "topic"], unique=False)

    with op.batch_alter_table("tests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("duration_mins", sa.INTEGER(), nullable=False, server_default="30"))
    for test_id, duration_mins in conn.execute(
        sa.text(
            "SELECT test_id, duration_mins FROM test_sections WHERE position = 0"
        )
    ).fetchall():
        conn.execute(
            sa.text("UPDATE tests SET duration_mins = :d WHERE id = :id"),
            {"d": duration_mins, "id": test_id},
        )

    op.execute(
        """
        CREATE TABLE test_questions_old (
            test_id VARCHAR NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
            question_id VARCHAR NOT NULL REFERENCES questions(id),
            position INTEGER NOT NULL,
            PRIMARY KEY (test_id, question_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO test_questions_old (test_id, question_id, position)
        SELECT ts.test_id, tq.question_id, tq.position
        FROM test_questions tq
        JOIN test_sections ts ON ts.id = tq.section_id
        """
    )
    op.execute("DROP TABLE test_questions")
    op.execute("ALTER TABLE test_questions_old RENAME TO test_questions")

    op.drop_table("test_sections")
