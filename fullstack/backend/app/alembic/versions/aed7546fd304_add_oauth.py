"""add oauth

Revision ID: aed7546fd304
Revises: 6ae4b435271c
Create Date: 2025-03-25 10:07:06.246145

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'aed7546fd304'
down_revision = '6ae4b435271c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('oauth_provider', sa.String(), nullable=True))
    op.add_column('user', sa.Column('oauth_id', sa.String(), nullable=True))
    op.add_column('user', sa.Column('oauth_access_token', sa.String(), nullable=True))
    op.add_column('user', sa.Column('oauth_refresh_token', sa.String(), nullable=True))
    op.add_column('user', sa.Column('oauth_token_expires_at', sa.DateTime(), nullable=True))
    op.alter_column('user', 'hashed_password',
               existing_type=sa.VARCHAR(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user', 'hashed_password',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('user', 'oauth_token_expires_at')
    op.drop_column('user', 'oauth_refresh_token')
    op.drop_column('user', 'oauth_access_token')
    op.drop_column('user', 'oauth_id')
    op.drop_column('user', 'oauth_provider')
    # ### end Alembic commands ###
