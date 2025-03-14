import asyncio
import os
from ai_chat.database import drop_db, init_db
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from ai_chat.database import engine

async def reset_database():
    # 删除现有数据库文件（如果存在）
    if os.path.exists("ai_chat.db"):
        os.remove("ai_chat.db")
    
    # 重新创建数据库表
    await drop_db()
    await init_db()
    
    # 添加 workspace_id 列（如果不存在）
    async with engine.begin() as conn:
        await conn.execute(text("""
            ALTER TABLE conversations 
            ADD COLUMN IF NOT EXISTS workspace_id INTEGER 
            REFERENCES workspaces(id) ON DELETE SET NULL
        """))

if __name__ == "__main__":
    asyncio.run(reset_database()) 