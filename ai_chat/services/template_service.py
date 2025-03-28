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

输入描述：{template_data.description}

严格按照以下JSON格式返回（不要添加任何其他内容）：
{{
    "name": "模板的中文名称（例如：会议通知模板）",
    "content": "模板的原始内容，使用 {{variable_name}} 格式的变量",
    "prompt_template": "模板的HTML内容，使用 {{variable_name}} 格式的变量",
    "variables": [
        {{
            "name": "变量名（英文小写加下划线）",
            "description": "变量的中文描述"
        }}
    ],
    "category": "模板分类（使用中文，例如：办公、通知、报告等）",
    "description": "模板的详细描述",
    "style": "模板的CSS样式",
    "author": "模板作者"
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
                required_fields = ["name", "content", "prompt_template", "variables"]
                if not all(key in result for key in required_fields):
                    raise ValueError("响应缺少必需的字段")
                
                # 创建模板对象
                db_template = Template(
                    name=result["name"],
                    description=result["description"],
                    content=result["content"],
                    prompt_template=result["prompt_template"],
                    variables={"variables": result["variables"]},
                    category=result.get("category", "通用"),
                    author=result.get("author", "AI助手"),
                    style=result.get("style", "")
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
                    "variables": db_template.variables["variables"],
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
            # 获取模板变量定义
            variables = template_data["variables"]
            var_definitions = {var["name"]: var["description"] for var in variables}
            
            # 构建包含所有变量的优化提示词
            variables_info = []
            for var_name, var_value in template_use.variable_values.items():
                if var_name in var_definitions:
                    variables_info.append(f"""变量名：{var_name}
描述：{var_definitions[var_name]}
当前值：{var_value}
---""")
            
            if variables_info:
                prompt = f"""请优化以下模板变量的值。对于每个变量，根据其描述优化用户输入的内容。

{chr(10).join(variables_info)}

要求：
1. 保持原意的同时，使表达更加专业、准确
2. 改正可能存在的语法错误
3. 优化语言表达，使其更加流畅
4. 如果是数字，保持原有格式
5. 如果是日期，统一格式为 YYYY-MM-DD
6. 如果内容合适，无需修改，直接返回原文

请按以下JSON格式返回优化结果（不要添加任何其他内容）：
{{
    "变量名1": "优化后的值1",
    "变量名2": "优化后的值2",
    ...
}}"""

                # 调用 LLM 优化所有变量值
                response = await self.llm_service.chat(
                    system="你是一个文本优化助手。请直接返回JSON格式的优化结果，不要添加任何解释或其他内容。",
                    history=[],
                    message=prompt
                )
                
                try:
                    # 解析优化后的值
                    optimized_values = json.loads(response.strip())
                except json.JSONDecodeError:
                    # 如果解析失败，尝试提取 JSON 部分
                    start = response.find('{')
                    end = response.rfind('}')
                    if start != -1 and end != -1:
                        try:
                            optimized_values = json.loads(response[start:end+1])
                        except json.JSONDecodeError:
                            # 如果还是失败，使用原始值
                            optimized_values = template_use.variable_values
                    else:
                        optimized_values = template_use.variable_values
            else:
                optimized_values = template_use.variable_values
                
            # 使用优化后的变量值替换模板内容
            content = template_data["prompt_template"]
            for var_name, var_value in optimized_values.items():
                if var_name in var_definitions:  # 只替换定义过的变量
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
                "variable_values": optimized_values,  # 返回优化后的变量值
                "original_values": template_use.variable_values,  # 保留原始值
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