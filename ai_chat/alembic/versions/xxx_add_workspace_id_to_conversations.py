"""add workspace_id to conversations

Revision ID: xxx
Revises: previous_revision_id
Create Date: 2024-03-13 19:02:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 添加 workspace_id 列
    op.add_column('conversations', sa.Column('workspace_id', sa.Integer(), nullable=True))
    
    # 添加外键约束
    op.create_foreign_key(
        'fk_conversations_workspace_id',
        'conversations', 'workspaces',
        ['workspace_id'], ['id'],
        ondelete='SET NULL'
    )

def downgrade():
    # 删除外键约束
    op.drop_constraint('fk_conversations_workspace_id', 'conversations', type_='foreignkey')
    
    # 删除 workspace_id 列
    op.drop_column('conversations', 'workspace_id') 