"""prediction_logs 表：预测复盘闭环（推荐落台账 + 开奖后对账命中/奖级）。

Revision ID: c41predlog01
Revises: b30fami1y01
Create Date: 2026-09-15
"""

import sqlalchemy as sa
from alembic import op

revision = "c41predlog01"
down_revision = "b30fami1y01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("dataset_kind", sa.String(12), nullable=False, server_default="real"),
        sa.Column("target_issue", sa.String(32), nullable=False),
        sa.Column("seed", sa.Integer, nullable=False, server_default="1"),
        sa.Column("strategy", sa.String(40), nullable=False, server_default=""),
        sa.Column("main_numbers", sa.JSON, nullable=False),
        sa.Column("special_numbers", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("checked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("hit_main", sa.Integer, nullable=True),
        sa.Column("hit_special", sa.Integer, nullable=True),
        sa.Column("prize", sa.String(40), nullable=True),
    )
    op.create_index("ix_pred_kind_issue", "prediction_logs", ["kind", "target_issue"])


def downgrade() -> None:
    op.drop_index("ix_pred_kind_issue", table_name="prediction_logs")
    op.drop_table("prediction_logs")
