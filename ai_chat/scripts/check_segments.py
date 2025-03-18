import sys
import os

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ai_chat.database import SessionLocal
from sqlalchemy import text

def check_segments():
    db = SessionLocal()
    try:
        # 检查所有文档
        print("\n=== Documents ===")
        docs = db.execute(text("SELECT * FROM documents")).fetchall()
        for doc in docs:
            print(f"\nDocument: {doc}")
            
        # 检查所有片段
        print("\n=== Document Segments ===")
        segments = db.execute(text("SELECT * FROM document_segments")).fetchall()
        for seg in segments:
            print(f"\nSegment: {seg}")
            
        # 检查所有工作空间关联
        print("\n=== Document Workspace Associations ===")
        workspaces = db.execute(text("SELECT * FROM document_workspaces")).fetchall()
        for ws in workspaces:
            print(f"\nWorkspace Association: {ws}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_segments() 