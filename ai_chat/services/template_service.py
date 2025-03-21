from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import re
from datetime import datetime
import json
from sqlalchemy import select

from ..models.template import Template
from ..api.schemas.template import (
    TemplateCreate,
    TemplateResponse,
    TemplateUse,
    TemplateUsageResponse
)
from ..chat.llm_factory import get_llm_service

class TemplateService:
    def __init__(self, db: Session):
        self.db = db
        self.llm_service = get_llm_service()

    async def create_template(self, template_data: TemplateCreate) -> Template:
        # 使用 LLM 生成结构化模板
        prompt = f"""请根据以下描述生成一个结构化的模板定义。

输入描述：{template_data.content}

严格按照以下JSON格式返回（不要添加任何其他内容）：
{{
    "prompt_template": "模板的HTML内容，使用 {{variable_name}} 格式的变量",
    "variables": [
        {{
            "name": "变量名（英文小写加下划线）",
            "description": "变量的中文描述"
        }}
    ],
    "category": "模板分类",
    "description": "模板的详细描述",
    "style": "模板的CSS样式"
}}"""

        try:
            # 调用 LLM 生成模板
            response = await self.llm_service.chat_completion([
                {"role": "system", "content": "你是一个JSON生成器。只返回JSON格式的数据，不要添加任何其他内容。"},
                {"role": "user", "content": prompt}
            ])
            
            # 清理响应内容
            content = response.get("content", "").strip()
            print(f"LLM Response: {content}")  # 添加日志
            
            # 尝试提取 JSON 部分
            try:
                # 查找第一个 { 和最后一个 }
                start = content.find('{')
                end = content.rfind('}')
                if start == -1 or end == -1:
                    raise ValueError("无法在响应中找到有效的 JSON")
                
                json_str = content[start:end+1]
                result = json.loads(json_str)
                
                # 验证必需的字段
                if not all(key in result for key in ["prompt_template", "variables"]):
                    raise ValueError("响应缺少必需的字段")
                
                # 创建模板对象
                db_template = Template(
                    name=template_data.name,
                    description=result.get("description", template_data.description),
                    content=template_data.content,  # 保存原始描述
                    prompt_template=result["prompt_template"],
                    variables={"variables": result["variables"]},  # 存储时使用字典格式
                    category=result.get("category", template_data.category),
                    author=template_data.author,
                    style=result.get("style", "")  # 保存CSS样式
                )
                
                self.db.add(db_template)
                await self.db.commit()
                await self.db.refresh(db_template)
                
                # 构造响应
                return {
                    "id": db_template.id,
                    "name": db_template.name,
                    "description": db_template.description,
                    "content": db_template.content,
                    "prompt_template": db_template.prompt_template,
                    "variables": db_template.variables["variables"],  # 返回时只返回变量列表
                    "category": db_template.category,
                    "author": db_template.author,
                    "created_at": db_template.created_at,
                    "updated_at": db_template.updated_at,
                    "version": db_template.version,
                    "status": db_template.status,
                    "usage_count": db_template.usage_count
                }
                
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {str(e)}")  # 添加错误日志
                raise ValueError(f"JSON解析错误: {str(e)}")
            
        except Exception as e:
            await self.db.rollback()
            print(f"Error creating template: {str(e)}")  # 添加错误日志
            raise Exception(f"创建模板时出错: {str(e)}")

    async def get_template(self, template_id: int) -> Optional[Template]:
        query = select(Template).where(Template.id == template_id)
        result = await self.db.execute(query)
        template = result.scalar_one_or_none()
        
        if template:
            return {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "content": template.content,
                "prompt_template": template.prompt_template,
                "variables": template.variables["variables"],  # 返回时只返回变量列表
                "category": template.category,
                "author": template.author,
                "created_at": template.created_at,
                "updated_at": template.updated_at,
                "version": template.version,
                "status": template.status,
                "usage_count": template.usage_count
            }
        return None

    async def list_templates(self, skip: int = 0, limit: int = 10) -> List[Template]:
        query = select(Template).offset(skip).limit(limit)
        result = await self.db.execute(query)
        templates = result.scalars().all()
        
        return [{
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "content": template.content,
            "prompt_template": template.prompt_template,
            "variables": template.variables["variables"],  # 返回时只返回变量列表
            "category": template.category,
            "author": template.author,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
            "version": template.version,
            "status": template.status,
            "usage_count": template.usage_count
        } for template in templates]

    async def use_template(self, template_id: int, template_use: TemplateUse) -> TemplateUsageResponse:
        template_data = await self.get_template(template_id)
        if not template_data:
            raise ValueError("Template not found")
            
        try:
            # 替换变量
            content = template_data["prompt_template"]
            for var_name, var_value in template_use.variable_values.items():
                content = content.replace(f"{{{var_name}}}", var_value)
                
            # 更新使用次数
            query = select(Template).where(Template.id == template_id)
            result = await self.db.execute(query)
            template = result.scalar_one_or_none()
            
            if template:
                template.usage_count += 1
                await self.db.commit()
            
            return {
                "id": 0,  # 这里应该是使用记录的ID
                "template_id": template_id,
                "variable_values": template_use.variable_values,
                "generated_content": content,
                "created_at": datetime.utcnow()
            }
            
        except Exception as e:
            await self.db.rollback()
            raise ValueError(f"使用模板时出错: {str(e)}")

    def _extract_variables(self, content: str) -> List[str]:
        """从内容中提取变量名"""
        pattern = r'\{([^}]+)\}'
        return list(set(re.findall(pattern, content))) 