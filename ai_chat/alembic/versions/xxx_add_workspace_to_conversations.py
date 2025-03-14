"""add workspace to conversations

Revision ID: xxx
Revises: previous_revision_id
Create Date: 2024-03-13 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('conversations', sa.Column('workspace_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'conversations', 'workspaces', ['workspace_id'], ['id'])

def downgrade():
    op.drop_constraint(None, 'conversations', type_='foreignkey')
    op.drop_column('conversations', 'workspace_id') 