from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_type = Column(String(100), nullable=True)
    mime_type = Column(String(255))
    size = Column(Integer, nullable=False, default=0)
    content = Column(Text)
    file_path = Column(String(255))  # 存储文件路径
    file_hash = Column(String(64))   # 文件 SHA256 哈希值
    version = Column(Integer, default=1)  # 文件版本号
    original_name = Column(String(255))  # 原始文件名
    status = Column(String(50), default="pending")
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 添加 dataset 关系
    dataset = relationship(
        "Dataset",
        back_populates="documents",
        foreign_keys=[dataset_id]
    )

    # 关系
    segments = relationship(
        "DocumentSegment",
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="DocumentSegment.document_id"
    )
    workspaces = relationship(
        "DocumentWorkspace",
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="DocumentWorkspace.document_id"
    )

class DocumentSegment(Base):
    __tablename__ = "document_segments"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    embedding = Column(Text)
    position = Column(Integer)
    word_count = Column(Integer)
    tokens = Column(Integer)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))

    # 关系
    document = relationship(
        "ai_chat.models.document.Document",
        back_populates="segments",
        foreign_keys=[document_id]
    )

class DocumentWorkspace(Base):
    __tablename__ = "document_workspaces"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="workspaces")
    workspace = relationship("Workspace", back_populates="documents") 