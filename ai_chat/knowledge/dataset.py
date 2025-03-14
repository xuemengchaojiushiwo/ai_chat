from ..models.types import Dataset, Document, DocumentSegment
from sqlalchemy.orm import Session
from typing import Optional, List

class DatasetManager:
    def __init__(self, db: Session):
        self.db = db
    
    def create_dataset(self, name: str, description: Optional[str] = None) -> Dataset:
        dataset = Dataset(name=name, description=description)
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset
    
    def get_dataset(self, dataset_id: int) -> Optional[Dataset]:
        return self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    def list_datasets(self) -> List[Dataset]:
        return self.db.query(Dataset).all()
    
    def add_document(self, dataset_id: int, name: str, content: str) -> Document:
        document = Document(
            dataset_id=dataset_id,
            name=name,
            content=content,
            status='pending'
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document 