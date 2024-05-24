"""empty message

Revision ID: fe6bfd1fa3d9
Revises: 24c70242ad73
Create Date: 2024-03-13 06:24:41.014815

"""
from typing import Sequence, Union

import fastapi_users_db_sqlalchemy
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fe6bfd1fa3d9"
down_revision: Union[str, None] = "24c70242ad73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("ml_model", sa.Column("env_vars", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("ml_model", "env_vars")
    # ### end Alembic commands ###