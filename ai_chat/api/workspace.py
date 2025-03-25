from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
from ai_chat.database import get_db
from pydantic import BaseModel
from datetime import datetime
from ai_chat.models.workspace import Workgroup as DBWorkgroup, Workspace as DBWorkspace
from ai_chat.models.document import Document, DocumentWorkspace
from sqlalchemy import func

router = APIRouter()

# 数据模型
class WorkgroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class WorkgroupCreate(WorkgroupBase):
    pass

class WorkgroupResponse(WorkgroupBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class WorkspaceBase(BaseModel):
    name: str
    description: Optional[str] = None
    group_id: int

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceResponse(WorkspaceBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    document_count: int = 0
    
    class Config:
        from_attributes = True

# 添加新的请求模型
class WorkspaceAssociationRequest(BaseModel):
    """工作空间关联请求模型"""
    document_ids: List[int]  # 修改为文档ID列表
    workspace_ids: List[int]

class WorkgroupUpdateRequest(WorkgroupCreate):
    group_id: int

class WorkspaceUpdateRequest(WorkspaceCreate):
    workspace_id: int

# 工作组接口
@router.get("/workgroups/list", response_model=List[WorkgroupResponse])
async def list_workgroups(db: AsyncSession = Depends(get_db)):
    """获取工作组列表"""
    result = await db.execute(select(DBWorkgroup))
    workgroups = result.scalars().all()
    return [
        WorkgroupResponse(
            id=wg.id,
            name=wg.name,
            description=wg.description or "",
            created_at=wg.created_at
        ) for wg in workgroups
    ]

@router.post("/workgroups/create", response_model=WorkgroupResponse)
async def create_workgroup(workgroup: WorkgroupCreate, db: AsyncSession = Depends(get_db)):
    """创建新工作组"""
    db_workgroup = DBWorkgroup(
        name=workgroup.name,
        description=workgroup.description
    )
    db.add(db_workgroup)
    await db.commit()
    await db.refresh(db_workgroup)
    return db_workgroup

@router.post("/workgroups/update", response_model=WorkgroupResponse)
async def update_workgroup(workgroup: WorkgroupUpdateRequest, db: AsyncSession = Depends(get_db)):
    """更新工作组信息"""
    result = await db.execute(
        select(DBWorkgroup).filter(DBWorkgroup.id == workgroup.group_id)
    )
    db_workgroup = result.scalar_one_or_none()
    
    if not db_workgroup:
        raise HTTPException(status_code=404, detail="Workgroup not found")
    
    for field, value in workgroup.dict(exclude={'group_id'}, exclude_unset=True).items():
        setattr(db_workgroup, field, value)
    
    await db.commit()
    await db.refresh(db_workgroup)
    return db_workgroup

@router.post("/workgroups/delete")
async def delete_workgroup(group_id: int, db: AsyncSession = Depends(get_db)):
    """删除工作组"""
    async with db as session:
        result = await session.execute(
            delete(DBWorkgroup).where(DBWorkgroup.id == group_id)
        )
        await session.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Workgroup not found")
    return {"status": "success"}

# 工作空间接口
@router.get("/workspaces/list", response_model=List[WorkspaceResponse])
async def list_workspaces(group_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    """获取工作空间列表"""
    query = select(DBWorkspace)
    if group_id:
        query = query.filter(DBWorkspace.group_id == group_id)
    result = await db.execute(query)
    workspaces = result.scalars().all()
    
    response_workspaces = []
    for workspace in workspaces:
        doc_count = await db.execute(
            select(func.count(DocumentWorkspace.document_id))
            .filter(DocumentWorkspace.workspace_id == workspace.id)
        )
        
        response_workspace = WorkspaceResponse(
            id=workspace.id,
            name=workspace.name,
            description=workspace.description or "",
            group_id=workspace.group_id,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at or workspace.created_at,
            document_count=doc_count.scalar() or 0
        )
        response_workspaces.append(response_workspace)
    
    return response_workspaces

@router.post("/workspaces/create", response_model=WorkspaceResponse)
async def create_workspace(workspace: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    """创建新工作空间"""
    result = await db.execute(
        select(DBWorkgroup).filter(DBWorkgroup.id == workspace.group_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workgroup not found")
    
    db_workspace = DBWorkspace(
        name=workspace.name,
        description=workspace.description,
        group_id=workspace.group_id
    )
    db.add(db_workspace)
    await db.commit()
    await db.refresh(db_workspace)
    return db_workspace

@router.post("/workspaces/update", response_model=WorkspaceResponse)
async def update_workspace(workspace: WorkspaceUpdateRequest, db: AsyncSession = Depends(get_db)):
    """更新工作空间信息"""
    result = await db.execute(
        select(DBWorkspace).filter(DBWorkspace.id == workspace.workspace_id)
    )
    db_workspace = result.scalar_one_or_none()
    
    if not db_workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    for field, value in workspace.dict(exclude={'workspace_id'}, exclude_unset=True).items():
        setattr(db_workspace, field, value)
    
    await db.commit()
    await db.refresh(db_workspace)
    return db_workspace

@router.post("/workspaces/delete")
async def delete_workspace(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """删除工作空间"""
    result = await db.execute(
        delete(DBWorkspace).where(DBWorkspace.id == workspace_id)
    )
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"status": "success"}

@router.get("/search", response_model=dict)
async def search(q: str, db: AsyncSession = Depends(get_db)):
    """搜索工作组和工作空间"""
    workgroups = await db.execute(
        select(DBWorkgroup).filter(
            (DBWorkgroup.name.ilike(f"%{q}%")) |
            (DBWorkgroup.description.ilike(f"%{q}%"))
        )
    )
    
    workspaces = await db.execute(
        select(DBWorkspace).filter(
            (DBWorkspace.name.ilike(f"%{q}%")) |
            (DBWorkspace.description.ilike(f"%{q}%"))
        )
    )
    
    return {
        "workgroups": workgroups.scalars().all(),
        "workspaces": workspaces.scalars().all()
    }

@router.post("/documents/link-workspaces")
async def link_document_workspace(
    request: WorkspaceAssociationRequest,
    db: AsyncSession = Depends(get_db)
):
    """关联多个文档到多个工作空间"""
    try:
        # 验证所有文档是否存在
        for document_id in request.document_ids:
            document = await db.execute(
                select(Document).filter(Document.id == document_id)
            )
            if not document.scalar_one_or_none():
                raise HTTPException(
                    status_code=404, 
                    detail=f"Document {document_id} not found"
                )

        # 验证所有工作空间是否存在
        for workspace_id in request.workspace_ids:
            workspace = await db.execute(
                select(DBWorkspace).filter(DBWorkspace.id == workspace_id)
            )
            if not workspace.scalar_one_or_none():
                raise HTTPException(
                    status_code=404, 
                    detail=f"Workspace {workspace_id} not found"
                )

        # 删除旧的关联关系
        await db.execute(
            delete(DocumentWorkspace).where(
                DocumentWorkspace.document_id.in_(request.document_ids)
            )
        )

        # 创建新的关联关系
        for document_id in request.document_ids:
            for workspace_id in request.workspace_ids:
                db_doc_workspace = DocumentWorkspace(
                    document_id=document_id,
                    workspace_id=workspace_id
                )
                db.add(db_doc_workspace)

        await db.commit()
        return {
            "status": "success",
            "message": f"Successfully linked {len(request.document_ids)} documents to {len(request.workspace_ids)} workspaces"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) 