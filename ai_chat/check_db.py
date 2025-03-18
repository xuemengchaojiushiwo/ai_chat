from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import reflection

def check_db():
    engine = create_engine('sqlite:///app.db')
    inspector = inspect(engine)
    
    print("Tables in database:")
    for table_name in inspector.get_table_names():
        print(f"\nTable: {table_name}")
        for column in inspector.get_columns(table_name):
            print(f"Column: {column['name']}, Type: {column['type']}")

if __name__ == '__main__':
    check_db() 