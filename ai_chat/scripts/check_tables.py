import sqlite3
import os

def check_tables():
    # Get the path to the ai_chat directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    db_path = os.path.join(parent_dir, 'ai_chat.db')
    
    print(f"Checking database at: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取所有表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("\nTables in database:")
    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}, Nullable: {col[3]}, Default: {col[4]}")
    
    conn.close()

if __name__ == '__main__':
    check_tables() 