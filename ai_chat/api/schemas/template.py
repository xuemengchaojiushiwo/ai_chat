from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class TemplateVariable(BaseModel):
    name: str = Field(..., example="meeting_title")
    description: str = Field(..., example="会议主题")

class TemplateBase(BaseModel):
    name: str = Field(..., example="会议通知模板")
    description: Optional[str] = Field(None, example="标准会议通知模板，包含会议主题、时间、地点等信息")
    content: str = Field(..., example="【会议通知】\n\n主题：{meeting_title}\n\n时间：{meeting_time}\n\n地点：{meeting_location}\n\n参会人员：{attendees}\n\n会议议程：\n{agenda}\n\n注意事项：\n1. 请准时参加\n2. 请提前准备相关材料\n3. 如有特殊情况请提前请假\n\n联系人：{contact_person}\n电话：{contact_phone}")
    category: Optional[str] = Field(None, example="办公")
    author: Optional[str] = Field(None, example="系统管理员")

class TemplateCreate(BaseModel):
    """创建模板的请求模型"""
    description: str = Field(
        ..., 
        description="模板描述，用于自动生成完整模板内容",
        example="标准会议通知模板，包含会议主题、时间、地点等信息"
    )

class TemplateResponse(TemplateBase):
    id: int = Field(..., example=1)
    prompt_template: str = Field(..., example="<article class='meeting-notice'><h1>{meeting_title}</h1><div class='meeting-info'><p>时间：{meeting_time}</p><p>地点：{meeting_location}</p></div></article>")
    variables: List[Dict[str, str]] = Field(..., example=[
        {"name": "meeting_title", "description": "会议主题"},
        {"name": "meeting_time", "description": "会议时间"},
        {"name": "meeting_location", "description": "会议地点"},
        {"name": "attendees", "description": "参会人员"},
        {"name": "agenda", "description": "会议议程"},
        {"name": "contact_person", "description": "联系人"},
        {"name": "contact_phone", "description": "联系电话"}
    ])
    created_at: datetime = Field(..., example="2024-03-20T10:00:00")
    updated_at: Optional[datetime] = Field(None, example="2024-03-20T10:00:00")
    version: int = Field(1, example=1)
    status: str = Field("active", example="active")
    usage_count: int = Field(0, example=0)

    class Config:
        from_attributes = True

class TemplateUse(BaseModel):
    variable_values: Dict[str, str] = Field(..., example={
        "meeting_title": "2024年第一季度工作总结会",
        "meeting_time": "2024年3月25日 14:00-16:00",
        "meeting_location": "公司三楼会议室",
        "attendees": "各部门负责人",
        "agenda": "1. 部门工作汇报\n2. 问题讨论\n3. 下季度计划制定",
        "contact_person": "张三",
        "contact_phone": "13800138000"
    })

class TemplateUsageResponse(BaseModel):
    id: int = Field(..., example=1)
    template_id: int = Field(..., example=1)
    variable_values: Dict[str, str] = Field(..., example={
        "meeting_title": "2024年第一季度工作总结会",
        "meeting_time": "2024年3月25日 14:00-16:00",
        "meeting_location": "公司三楼会议室",
        "attendees": "各部门负责人",
        "agenda": "1. 部门工作汇报\n2. 问题讨论\n3. 下季度计划制定",
        "contact_person": "张三",
        "contact_phone": "13800138000"
    })
    generated_content: str = Field(..., example="【会议通知】\n\n主题：2024年第一季度工作总结会\n\n时间：2024年3月25日 14:00-16:00\n\n地点：公司三楼会议室\n\n参会人员：各部门负责人\n\n会议议程：\n1. 部门工作汇报\n2. 问题讨论\n3. 下季度计划制定\n\n注意事项：\n1. 请准时参加\n2. 请提前准备相关材料\n3. 如有特殊情况请提前请假\n\n联系人：张三\n电话：13800138000")
    created_at: datetime = Field(..., example="2024-03-20T10:00:00")

class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, example="会议通知模板")
    description: Optional[str] = Field(None, example="标准会议通知模板，包含会议主题、时间、地点等信息")
    content: Optional[str] = Field(None, example="【会议通知】\n\n主题：{meeting_title}\n\n时间：{meeting_time}")
    category: Optional[str] = Field(None, example="办公")
    status: Optional[str] = Field(None, example="active") 