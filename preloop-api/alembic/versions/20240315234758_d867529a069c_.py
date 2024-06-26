"""empty message

Revision ID: d867529a069c
Revises: fe6bfd1fa3d9
Create Date: 2024-03-15 23:47:58.215284

"""
from typing import Sequence, Union

import fastapi_users_db_sqlalchemy
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d867529a069c"
down_revision: Union[str, None] = "fe6bfd1fa3d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "ml_model_training_jobs", sa.Column("ecs_task_arn", sa.String(), nullable=True)
    )
    op.add_column(
        "ml_model_training_jobs",
        sa.Column("cloudwatch_log_group_name", sa.String(), nullable=True),
    )
    op.add_column(
        "ml_model_training_jobs",
        sa.Column("cloudwatch_log_stream_name", sa.String(), nullable=True),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("ml_model_training_jobs", "cloudwatch_log_stream_name")
    op.drop_column("ml_model_training_jobs", "cloudwatch_log_group_name")
    op.drop_column("ml_model_training_jobs", "ecs_task_arn")
    # ### end Alembic commands ###
