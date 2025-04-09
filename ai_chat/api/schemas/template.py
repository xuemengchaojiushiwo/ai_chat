from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


class TemplateVariable(BaseModel):
    name: str = Field(...)
    description: str = Field(...)
    required: bool = Field(default=True)

class TemplateBase(BaseModel):
    name: str = Field(...)
    description: Optional[str] = Field(None)
    content: str = Field(...)
    category: Optional[str] = Field(None)
    author: Optional[str] = Field(None)

class TemplateCreate(BaseModel):
    """创建模板的请求模型"""
    description: str = Field(
        ..., 
        description="模板描述，用于自动生成完整模板内容"
    )

class TemplateUpdate(BaseModel):
    """更新模板的请求模型"""
    name: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    content: Optional[str] = Field(None)
    category: Optional[str] = Field(None)
    status: Optional[str] = Field(None)
    variables: Optional[List[TemplateVariable]] = Field(None, description="要更新的变量列表")

class TemplateVariableOperation(BaseModel):
    """单个变量的操作模型"""
    operation: str = Field(..., description="操作类型：add 或 remove")
    variable: TemplateVariable = Field(..., description="要操作的变量")

class TemplateVariableUpdate(BaseModel):
    """更新模板变量的请求模型"""
    operation: str = Field(..., description="操作类型：add 或 remove")
    variable: TemplateVariable = Field(..., description="要操作的变量")

class TemplateResponse(TemplateBase):
    id: int = Field(...)
    prompt_template: str = Field(...)
    variables: List[Dict[str, Any]] = Field(...)
    created_at: datetime = Field(...)
    updated_at: Optional[datetime] = Field(None)
    version: int = Field(1)
    status: str = Field("active")
    usage_count: int = Field(0)

    class Config:
        from_attributes = True

class TemplateUse(BaseModel):
    variable_values: Dict[str, str] = Field(...)

class TemplateUsageResponse(BaseModel):
    id: int = Field(...)
    template_id: int = Field(...)
    variable_values: Dict[str, str] = Field(...)
    generated_content: str = Field(...)
    created_at: datetime = Field(...)