from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from ...database import get_db
from ...services.template_service import TemplateService
from ..schemas import (
    TemplateBase,
    TemplateCreate,
    TemplateResponse,
    TemplateUse,
    TemplateUsageResponse,
    TemplateUpdate,
    TemplateVariable
)

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