import sys
import os

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from datetime import datetime
import json
from ai_chat.database import SessionLocal, Base, engine
from ai_chat.models.workspace import Workgroup, Workspace
from ai_chat.models.dataset import Dataset
from ai_chat.models.document import Document, DocumentSegment, DocumentWorkspace
from sqlalchemy import text, inspect

def init_db():
    db = SessionLocal()
    try:
        # Drop all tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        for table in tables:
            db.execute(text(f'DROP TABLE IF EXISTS {table}'))
        db.commit()

        # Create all tables
        Base.metadata.create_all(bind=engine)

        # Create default workgroup
        workgroup = Workgroup(
            name="default",
            description="Default workgroup",
            created_at=datetime.utcnow()
        )
        db.add(workgroup)
        db.flush()  # Flush to get the workgroup ID

        # Create default workspace
        workspace = Workspace(
            name="default",
            description="Default workspace",
            group_id=workgroup.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(workspace)
        db.flush()  # Flush to get the workspace ID

        # Create default dataset
        dataset = Dataset(
            name="default",
            description="Default dataset",
            created_at=datetime.utcnow()
        )
        db.add(dataset)
        db.flush()  # Flush to get the dataset ID

        # Create example document
        document = Document(
            name="example.txt",
            description="测试文档",
            file_type="text/plain",
            mime_type="text/plain",
            size=1024,
            content="本项目使用了以下技术栈：\n1. 后端：Python FastAPI框架\n2. 数据库：SQLite + SQLAlchemy ORM\n3. 异步处理：使用Python asyncio\n4. API文档：Swagger/OpenAPI\n5. 向量检索：基于embedding的相似度搜索",
            status="completed",
            dataset_id=dataset.id,
            created_at=datetime.utcnow()
        )
        db.add(document)
        db.flush()  # Flush to get the document ID

        # Create document workspace association
        doc_workspace = DocumentWorkspace(
            document_id=document.id,
            workspace_id=workspace.id,
            created_at=datetime.utcnow()
        )
        db.add(doc_workspace)

        # Create document segments with example embedding
        example_embedding = [0.1] * 1024  # Create a 1024-dimensional embedding
        segment = DocumentSegment(
            document_id=document.id,
            content="本项目使用了以下技术栈：\n1. 后端：Python FastAPI框架\n2. 数据库：SQLite + SQLAlchemy ORM\n3. 异步处理：使用Python asyncio\n4. API文档：Swagger/OpenAPI\n5. 向量检索：基于embedding的相似度搜索",
            embedding=json.dumps(example_embedding),  # Store embedding as JSON string
            position=0,
            word_count=50,
            tokens=100,
            status="completed",
            created_at=datetime.utcnow(),
            dataset_id=dataset.id
        )
        db.add(segment)

        # Commit all changes
        db.commit()
        print("Database initialized successfully!")

    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_db() 