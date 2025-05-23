"""add budget

Revision ID: 31adec2c693f
Revises: 878e38c33467
Create Date: 2025-03-04 06:58:27.636486

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '31adec2c693f'
down_revision = '878e38c33467'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('budget',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'active', name='uq_budget')
    )
    op.create_table('budget_entry',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('amount', sa.Numeric(), nullable=False),
    sa.Column('budget_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['budget_id'], ['budget.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('budget_category_link',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('budget_id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['budget_id'], ['budget.id'], ),
    sa.ForeignKeyConstraint(['category_id'], ['category.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    connection = op.get_bind()
    # make sure to add rls
    for table_name in ["budget", "budget_entry", "budget_category_link"]:
            connection.execute(sa.text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
            connection.execute(sa.text(f"""
                CREATE POLICY user_isolation_policy ON {table_name}
                USING (user_id = current_setting('app.current_user_id')::int);
            """))
            print(f"✔ RLS applied to {table_name}")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('budget_category_link')
    op.drop_table('budget_entry')
    op.drop_table('budget')
    # ### end Alembic commands ###
