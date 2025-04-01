"""migrate to mysql and chroma

Revision ID: migrate_to_mysql_chroma
Revises: 
Create Date: 2024-03-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'migrate_to_mysql_chroma'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 修改document_segments表
    with op.batch_alter_table('document_segments') as batch_op:
        # 删除embedding列
        batch_op.drop_column('embedding')
        # 添加chroma_id列
        batch_op.add_column(sa.Column('chroma_id', sa.String(255), unique=True))

def downgrade():
    # 恢复原始结构
    with op.batch_alter_table('document_segments') as batch_op:
        # 删除chroma_id列
        batch_op.drop_column('chroma_id')
        # 恢复embedding列
        batch_op.add_column(sa.Column('embedding', sa.Text())) 