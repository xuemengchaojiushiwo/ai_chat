"""add citations to messages

Revision ID: xxx
Revises: previous_revision_id
Create Date: 2024-03-13 18:31:42.675

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'xxx'
down_revision = 'previous_revision_id'  # 替换为你的上一个迁移版本ID
branch_labels = None
depends_on = None

def upgrade():
    # 添加 citations 列
    op.add_column('messages', sa.Column('citations', sa.JSON(), nullable=True))

def downgrade():
    # 删除 citations 列
    op.drop_column('messages', 'citations') 