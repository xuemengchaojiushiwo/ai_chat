import sys
import os

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ai_chat.database import SessionLocal
from ai_chat.models.workspace import Workspace
from ai_chat.models.document import Document, DocumentWorkspace
from sqlalchemy import text

def check_conversations():
    db = SessionLocal()
    try:
        # 检查所有对话
        conversations = db.execute(text("SELECT id, title, workspace_id FROM conversations")).fetchall()
        print("All conversations:")
        for conv in conversations:
            print(f"\nConversation: {conv}")
            
            # 如果有工作空间ID，检查该工作空间的文档
            if conv[2]:  # workspace_id
                workspace_id = conv[2]
                docs = db.execute(text("""
                    SELECT d.* FROM documents d
                    JOIN document_workspaces dw ON d.id = dw.document_id
                    WHERE dw.workspace_id = :workspace_id
                """), {"workspace_id": workspace_id}).fetchall()
                print(f"Documents in workspace {workspace_id}:")
                for doc in docs:
                    print(f"Document: {doc}")
            else:
                print("No workspace associated with this conversation")
                
        # 检查所有工作空间
        print("\nAll workspaces:")
        workspaces = db.execute(text("SELECT * FROM workspaces")).fetchall()
        for ws in workspaces:
            print(f"Workspace: {ws}")
            
        # 检查所有文档工作空间关联
        print("\nAll document-workspace associations:")
        doc_workspaces = db.execute(text("SELECT * FROM document_workspaces")).fetchall()
        for dw in doc_workspaces:
            print(f"Document-Workspace: {dw}")
            
    finally:
        db.close()

if __name__ == '__main__':
    check_conversations() 