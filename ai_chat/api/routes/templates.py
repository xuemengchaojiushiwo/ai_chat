from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..schemas import (
    TemplateCreate,
    TemplateResponse,
    TemplateUse,
    TemplateUsageResponse,
    TemplateVariableUpdate
)
from ...database import get_db
from ...services.template_service import TemplateService

router = APIRouter(
    prefix="/api/v1/templates",
    tags=["模板管理"]
)

@router.post("/create", response_model=TemplateResponse)
async def create_template(
    template: TemplateCreate,
    db: Session = Depends(get_db)
):
    """创建新模板，使用 LLM 优化内容并提取变量"""
    service = TemplateService(db)
    return await service.create_template(template)

@router.get("/detail/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: int, db: Session = Depends(get_db)):
    """获取模板详情"""
    service = TemplateService(db)
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.get("/list", response_model=List[TemplateResponse])
async def list_templates(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """获取模板列表"""
    service = TemplateService(db)
    return await service.list_templates(skip, limit)

@router.post("/generate", response_model=TemplateUsageResponse)
async def use_template(
    template_id: int,
    template_use: TemplateUse,
    db: Session = Depends(get_db)
):
    """使用模板生成内容，并通过 LLM 优化"""
    service = TemplateService(db)
    return await service.use_template(template_id, template_use)

@router.post("/{template_id}/variables", response_model=TemplateResponse)
async def update_template_variables(
    template_id: int,
    update: TemplateVariableUpdate,
    db: Session = Depends(get_db)
):
    """更新模板变量，支持添加、删除或更新单个变量
    
    - operation: add - 添加新变量
    - operation: remove - 删除现有变量
    - operation: update - 更新变量名称和描述
    """
    service = TemplateService(db)
    return await service.update_template_variables(
        template_id, 
        update.operation, 
        update.variable,
        update.old_name
    ) 