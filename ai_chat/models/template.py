from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from ..database import Base

class Template(Base):
    __tablename__ = 'templates'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    prompt_template = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)
    category = Column(String(50), nullable=True, index=True)
    author = Column(String(100), nullable=True)
    style = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default='active')
    usage_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, name, content, prompt_template, description=None, variables=None, 
                 category=None, author=None, style=None):
        self.name = name
        self.description = description
        self.content = content
        self.prompt_template = prompt_template
        self.variables = variables or {}
        self.category = category
        self.author = author
        self.style = style

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'content': self.content,
            'prompt_template': self.prompt_template,
            'variables': self.variables,
            'category': self.category,
            'author': self.author,
            'style': self.style,
            'version': self.version,
            'status': self.status,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 