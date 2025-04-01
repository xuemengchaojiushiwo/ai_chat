"""add chroma_id field

Revision ID: 20240328_add_chroma_id
Revises: migrate_to_mysql_chroma
Create Date: 2024-03-28 11:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240328_add_chroma_id'
down_revision = 'migrate_to_mysql_chroma'
branch_labels = None
depends_on = None

def upgrade():
    # 修改document_segments表
    op.add_column('document_segments', sa.Column('chroma_id', sa.String(255), unique=True))

def downgrade():
    # 恢复原始结构
    op.drop_column('document_segments', 'chroma_id') 