"""upd outliers and ml tables

Revision ID: 4d456687a54b
Revises: 66247c2ba633
Create Date: 2025-05-23 11:43:02.315811

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d456687a54b"
down_revision: Union[str, None] = "66247c2ba633"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "ml_predictions_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("result_value", sa.Text(), nullable=False),
        sa.Column("diagnosis_name", sa.Text(), nullable=False),
        sa.Column("iteration_num", sa.Integer(), nullable=False),
        sa.Column("iteration_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ml_predictions_records_id"),
        "ml_predictions_records",
        ["id"],
        unique=False,
    )
    op.create_table(
        "outliers_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_record_id", sa.Integer(), nullable=False),
        sa.Column("outliers_search_iteration_num", sa.Integer(), nullable=False),
        sa.Column(
            "outliers_search_iteration_datetime",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["raw_record_id"],
            ["raw_records.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("raw_record_id"),
    )
    op.create_index(
        op.f("ix_outliers_records_id"), "outliers_records", ["id"], unique=False
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_outliers_records_id"), table_name="outliers_records")
    op.drop_table("outliers_records")
    op.drop_index(
        op.f("ix_ml_predictions_records_id"), table_name="ml_predictions_records"
    )
    op.drop_table("ml_predictions_records")
    # ### end Alembic commands ###
