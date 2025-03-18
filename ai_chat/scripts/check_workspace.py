import sys
import os

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ai_chat.database import SessionLocal
from sqlalchemy import text

def check_workspace():
    db = SessionLocal()
    try:
        # 检查工作空间2的信息
        print("\n=== 工作空间2的信息 ===")
        workspace = db.execute(text("SELECT * FROM workspaces WHERE id = 2")).fetchone()
        print(f"Workspace: {workspace}")
        
        # 检查工作空间2的文档关联
        print("\n=== 工作空间2的文档关联 ===")
        doc_workspaces = db.execute(text("""
            SELECT dw.*, d.name as doc_name, d.content as doc_content 
            FROM document_workspaces dw 
            JOIN documents d ON d.id = dw.document_id 
            WHERE dw.workspace_id = 2
        """)).fetchall()
        for dw in doc_workspaces:
            print(f"\nDocument workspace association: {dw}")
            
        # 检查文档片段
        print("\n=== 文档片段 ===")
        segments = db.execute(text("""
            SELECT ds.* 
            FROM document_segments ds
            JOIN documents d ON d.id = ds.document_id
            JOIN document_workspaces dw ON d.id = dw.document_id
            WHERE dw.workspace_id = 2
        """)).fetchall()
        for seg in segments:
            print(f"\nSegment: {seg}")
            
    finally:
        db.close()

if __name__ == '__main__':
    check_workspace() 