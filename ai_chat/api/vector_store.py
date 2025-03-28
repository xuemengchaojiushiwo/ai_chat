from fastapi import APIRouter, HTTPException
import logging
from ..services.vector_store import vector_store
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/vector-store",
    tags=["向量存储"]
)

class ResetResponse(BaseModel):
    status: str
    message: str

@router.post("/reset", response_model=ResetResponse)
async def reset_vector_store():
    """重置向量存储，清空所有数据并重新初始化"""
    try:
        # 调用 vector_store 的重置方法
        await vector_store.delete_embeddings(
            ids=vector_store.collection.get()["ids"]
        )
        return {
            "status": "success",
            "message": "Vector store has been reset successfully"
        }
    except Exception as e:
        logger.error(f"Error resetting vector store: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset vector store: {str(e)}"
        ) 