import sys
import os

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from ai_chat.database import SessionLocal
from sqlalchemy import text, inspect

def check_db():
    db = SessionLocal()
    try:
        # Get the inspector
        inspector = inspect(db.bind)

        # Get all table names
        print("\nTables in database:")
        tables = inspector.get_table_names()
        
        if not tables:
            print("No tables found in database!")
            return

        # For each table, get its columns
        for table_name in tables:
            print(f"\nTable: {table_name}")
            for column in inspector.get_columns(table_name):
                print(f"Column: {column['name']}, Type: {column['type']}")

    finally:
        db.close()

if __name__ == "__main__":
    check_db() 