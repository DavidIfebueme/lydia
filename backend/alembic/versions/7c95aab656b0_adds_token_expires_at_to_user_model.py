"""adds token expires at to user model

Revision ID: 7c95aab656b0
Revises: b4dcca4df2b5
Create Date: 2025-06-17 14:46:36.751232

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c95aab656b0'
down_revision: Union[str, None] = 'b4dcca4df2b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'token_expires_at')
    # ### end Alembic commands ###
