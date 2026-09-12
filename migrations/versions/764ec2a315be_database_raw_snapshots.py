"""Durable compressed snapshots for stateless cloud deployments."""

import sqlalchemy as sa
from alembic import op

revision = "764ec2a315be"
down_revision = "5a2fdefb3090"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "raw_snapshots",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("raw_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("raw_snapshots")
