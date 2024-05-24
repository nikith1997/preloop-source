"""empty message

Revision ID: 9ffe554168f2
Revises: d608446ea5e4
Create Date: 2024-03-05 05:25:49.543079

"""
from typing import Sequence, Union

import fastapi_users_db_sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9ffe554168f2"
down_revision: Union[str, None] = "d608446ea5e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "hosted_ml_models",
        sa.Column(
            "user_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
    )
    op.add_column(
        "ml_model_versions",
        sa.Column(
            "user_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
    )
    op.alter_column(
        "ml_model_versions",
        "ml_model_metrics",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
        existing_server_default=sa.text("'{}'::jsonb"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "ml_model_versions",
        "ml_model_metrics",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        existing_server_default=sa.text("'{}'::jsonb"),
    )
    op.drop_column("ml_model_versions", "user_id")
    op.drop_column("hosted_ml_models", "user_id")
    # ### end Alembic commands ###
