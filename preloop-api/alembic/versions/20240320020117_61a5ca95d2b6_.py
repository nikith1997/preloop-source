"""empty message

Revision ID: 61a5ca95d2b6
Revises: 86d9102e9b36
Create Date: 2024-03-20 02:01:17.346500

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import fastapi_users_db_sqlalchemy


# revision identifiers, used by Alembic.
revision: str = '61a5ca95d2b6'
down_revision: Union[str, None] = '86d9102e9b36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('hosted_ml_models_load_balancer_id_fkey', 'hosted_ml_models', type_='foreignkey')
    op.create_foreign_key(op.f('hosted_ml_models_load_balancer_id_fkey'), 'hosted_ml_models', 'org_load_balancers', ['load_balancer_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f('hosted_ml_models_load_balancer_id_fkey'), 'hosted_ml_models', type_='foreignkey')
    op.create_foreign_key('hosted_ml_models_load_balancer_id_fkey', 'hosted_ml_models', 'org_load_balancers', ['load_balancer_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###
