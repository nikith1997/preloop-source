"""empty message

Revision ID: 392d0806fe1d
Revises: 10bf5a7498f8
Create Date: 2024-02-17 07:25:32.380682

"""
from typing import Sequence, Union

import fastapi_users_db_sqlalchemy
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "392d0806fe1d"
down_revision: Union[str, None] = "10bf5a7498f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("ml_model", sa.Column("latest_version", sa.Integer(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("ml_model", "latest_version")
    # ### end Alembic commands ###