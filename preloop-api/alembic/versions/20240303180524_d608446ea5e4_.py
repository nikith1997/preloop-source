"""empty message

Revision ID: d608446ea5e4
Revises: 8a6e2f4ad5db
Create Date: 2024-03-03 18:05:24.474966

"""
from typing import Sequence, Union

import fastapi_users_db_sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d608446ea5e4"
down_revision: Union[str, None] = "8a6e2f4ad5db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "ml_model",
        sa.Column(
            "ml_model_data_flow", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("ml_model", "ml_model_data_flow")
    # ### end Alembic commands ###