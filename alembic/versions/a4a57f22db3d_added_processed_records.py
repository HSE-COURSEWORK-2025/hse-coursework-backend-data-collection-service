"""added processed records

Revision ID: a4a57f22db3d
Revises: 7b398e8250a5
Create Date: 2025-06-17 15:14:48.538715

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4a57f22db3d"
down_revision: Union[str, None] = "7b398e8250a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "processed_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data_type", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_processed_records_email"), "processed_records", ["email"], unique=False
    )
    op.create_index(
        op.f("ix_processed_records_id"), "processed_records", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_processed_records_time"), "processed_records", ["time"], unique=False
    )
    op.create_table(
        "processed_records_outliers_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("processed_record_id", sa.Integer(), nullable=False),
        sa.Column("outliers_search_iteration_num", sa.Integer(), nullable=False),
        sa.Column(
            "outliers_search_iteration_datetime",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["processed_record_id"],
            ["processed_records.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_processed_records_outliers_records_id"),
        "processed_records_outliers_records",
        ["id"],
        unique=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(
        op.f("ix_processed_records_outliers_records_id"),
        table_name="processed_records_outliers_records",
    )
    op.drop_table("processed_records_outliers_records")
    op.drop_index(op.f("ix_processed_records_time"), table_name="processed_records")
    op.drop_index(op.f("ix_processed_records_id"), table_name="processed_records")
    op.drop_index(op.f("ix_processed_records_email"), table_name="processed_records")
    op.drop_table("processed_records")
    # ### end Alembic commands ###
