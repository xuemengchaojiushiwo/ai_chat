from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy.orm import Session
import re
from datetime import datetime
import json
from sqlalchemy import select
import time
import logging
import functools
import asyncio
from collections import OrderedDict

from ..models.template import Template
from ..api.schemas.template import (
    TemplateCreate,
    TemplateResponse,
    TemplateUse,
    TemplateUsageResponse
)
from ..chat.llm_factory import get_llm_service

logger = logging.getLogger(__name__)

class LRUCache:
    """简单的LRU缓存实现"""
    def __init__(self, capacity: int = 100):
        self.cache = OrderedDict()
        self.capacity = capacity
        
    def get(self, key):
        if key not in self.cache:
            return None
        # 移动到最近使用
        value = self.cache.pop(key)
        self.cache[key] = value
        return value
        
    def put(self, key, value):
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.capacity:
            # 移除最近最少使用的项
            self.cache.popitem(last=False)
        self.cache[key] = value

class TemplateService:
    def __init__(self, db: Session):
        self.db = db
        self.llm_service = get_llm_service()
        self._json_cache = LRUCache(capacity=50)  # 限制缓存大小为50项
    
    def _extract_json(self, text: str) -> Dict:
        """智能提取JSON内容，处理可能的格式问题"""
        # 尝试直接解析整个字符串
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试查找JSON对象
        try:
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                return json.loads(text[start:end+1])
        except json.JSONDecodeError:
            pass
            
        # 尝试使用正则表达式提取
        try:
            import re
            match = re.search(r'({[\s\S]*})', text)
            if match:
                return json.loads(match.group(1))
        except (json.JSONDecodeError, AttributeError):
            pass
            
        raise ValueError(f"无法从文本中提取有效的JSON: {text[:100]}...")

    async def create_template(self, template_data: TemplateCreate) -> Template:
        """创建新模板 - 性能优化版本"""
        start_time = time.time()
        logger.info(f"开始创建模板: {template_data.description[:50]}...")
        
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
    "style": "模板的CSS样式（可选）",
    "author": "模板作者（可选）"
}}"""

        try:
            # 优化点1: 缓存类似的请求
            cache_key = template_data.description
            cached_result = self._json_cache.get(cache_key)
            if cached_result:
                logger.info(f"使用缓存的模板定义")
                result = cached_result
            else:
                # 调用 LLM 生成模板 - 超时控制
                llm_start_time = time.time()
                try:
                    # 使用asyncio.wait_for添加超时控制
                    response = await asyncio.wait_for(
                        self.llm_service.chat_completion([
                            {"role": "system", "content": "你是一个JSON生成器。只返回JSON格式的数据，不要添加任何其他内容。"},
                            {"role": "user", "content": prompt}
                        ]), 
                        timeout=30.0  # 30秒超时
                    )
                    llm_elapsed = time.time() - llm_start_time
                    logger.info(f"LLM响应时间: {llm_elapsed:.2f}秒")
                    
                    # 清理和解析响应
                    content = response.get("content", "").strip()
                    logger.debug(f"LLM响应: {content[:200]}...")
                    result = self._extract_json(content)
                    
                    # 优化点2: 缓存结果
                    self._json_cache.put(cache_key, result)
                except asyncio.TimeoutError:
                    logger.warning("LLM请求超时，使用基本模板")
                    # 超时时使用基本模板结构
                    result = {
                        "name": template_data.description[:20],
                        "content": "模板内容 - 请编辑",
                        "prompt_template": "<div>模板内容 - 请编辑</div>",
                        "variables": [],
                        "category": "通用",
                        "description": template_data.description,
                        "style": "",
                        "author": "系统"
                    }
            
            # 验证必需的字段
            required_fields = ["name", "content", "prompt_template", "variables"]
            if not all(key in result for key in required_fields):
                for key in required_fields:
                    if key not in result:
                        result[key] = "" if key != "variables" else []
                logger.warning(f"模板缺少必需的字段，已添加默认值")
            
            # 优化点3: 并行处理数据库操作
            # 创建模板对象
            db_template = Template(
                name=result.get("name", template_data.description[:20]),
                description=result.get("description", template_data.description),
                content=result.get("content", ""),
                prompt_template=result.get("prompt_template", ""),
                variables={"variables": result.get("variables", [])},
                category=result.get("category", "通用"),
                author=result.get("author", "AI助手"),
                style=result.get("style", "")
            )
            
            # 数据库操作
            self.db.add(db_template)
            await self.db.commit()
            await self.db.refresh(db_template)
            
            # 构造响应
            response_data = {
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
            
            total_elapsed = time.time() - start_time
            logger.info(f"模板创建完成，耗时: {total_elapsed:.2f}秒")
            return response_data
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建模板时出错: {str(e)}")
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
        """使用模板生成内容 - 性能优化版本"""
        start_time = time.time()
        logger.info(f"开始使用模板 {template_id} 生成内容")
        
        # 优化点1: 异步并行获取模板数据
        template_data_task = asyncio.create_task(self.get_template(template_id))
        
        try:
            # 等待模板数据
            template_data = await template_data_task
            if not template_data:
                raise ValueError("Template not found")
                
            # 获取模板变量定义
            variables = template_data["variables"]
            var_definitions = {var["name"]: var["description"] for var in variables}
            
            # 优化点2: 跳过不必要的LLM调用
            # 如果没有变量或所有变量都为空，直接使用原始值
            if not template_use.variable_values or all(not val for val in template_use.variable_values.values()):
                logger.info("跳过变量优化，使用原始值")
                optimized_values = template_use.variable_values
            else:
                # 构建包含所有变量的优化提示词
                variables_info = []
                for var_name, var_value in template_use.variable_values.items():
                    if var_name in var_definitions:
                        variables_info.append(f"""变量名：{var_name}
描述：{var_definitions[var_name]}
当前值：{var_value}
---""")
                
                if variables_info:
                    # 优化点3: 修改LLM提示，使其更尊重原始输入
                    prompt = f"""请对以下模板变量值进行最小化优化，保持原始含义：

{chr(10).join(variables_info)}

优化规则：
1. 仅修正明显的语法错误
2. 仅统一日期格式为YYYY-MM-DD
3. 保持用户原始表达意图
4. 不要改变用户的核心意思
5. 不要添加额外的解释或总结
6. 不要改变数字和关键信息

仅返回JSON格式：
{{
    "变量名1": "优化后的值1",
    "变量名2": "优化后的值2"
}}"""

                    # 优化点4: 添加超时控制
                    try:
                        llm_start = time.time()
                        response = await asyncio.wait_for(
                            self.llm_service.chat(
                                system="你是文本优化助手。请最小化修改用户输入，仅修正明显错误。直接返回JSON格式结果，不要添加任何解释。",
                                history=[],
                                message=prompt
                            ),
                            timeout=20.0  # 20秒超时
                        )
                        logger.info(f"LLM响应时间: {time.time() - llm_start:.2f}秒")
                        
                        # 优化点5: 使用通用JSON提取函数
                        try:
                            optimized_values = self._extract_json(response)
                            # 验证优化后的值是否保持了原始含义
                            for var_name, orig_value in template_use.variable_values.items():
                                if var_name in optimized_values:
                                    opt_value = optimized_values[var_name]
                                    # 如果优化后的值完全改变了原始含义，使用原始值
                                    if not self._is_meaning_preserved(orig_value, opt_value):
                                        logger.warning(f"变量 {var_name} 的优化值改变了原始含义，使用原始值")
                                        optimized_values[var_name] = orig_value
                        except ValueError:
                            logger.warning("无法解析LLM响应，使用原始值")
                            optimized_values = template_use.variable_values
                    except asyncio.TimeoutError:
                        logger.warning("LLM优化请求超时，使用原始值")
                        optimized_values = template_use.variable_values
                else:
                    optimized_values = template_use.variable_values
                    
            # 优化点6: 更高效的变量替换
            content = template_data["prompt_template"]
            # 预编译正则表达式
            var_pattern = re.compile(r'\{([^}]+)\}')
            # 一次性替换所有变量
            matches = var_pattern.findall(content)
            for var_name in matches:
                if var_name in optimized_values and var_name in var_definitions:
                    content = content.replace(f"{{{var_name}}}", optimized_values[var_name])
            
            # 优化点7: 异步更新使用次数
            async def update_usage_count():
                query = select(Template).where(Template.id == template_id)
                result = await self.db.execute(query)
                template = result.scalar_one_or_none()
                if template:
                    template.usage_count += 1
                    await self.db.commit()
            
            # 不等待更新完成，让它在后台运行
            asyncio.create_task(update_usage_count())
            
            # 构建响应
            response = {
                "id": 0,  # 这里应该是使用记录的ID
                "template_id": template_id,
                "variable_values": optimized_values,
                "original_values": template_use.variable_values,
                "generated_content": content,
                "created_at": datetime.utcnow()
            }
            
            total_elapsed = time.time() - start_time
            logger.info(f"模板使用完成，耗时: {total_elapsed:.2f}秒")
            return response
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"使用模板时出错: {str(e)}")
            raise ValueError(f"使用模板时出错: {str(e)}")

    def _is_meaning_preserved(self, original: str, optimized: str) -> bool:
        """检查优化后的文本是否保持了原始含义"""
        # 移除空白字符和标点符号进行比较
        def clean_text(text: str) -> str:
            return re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        
        orig_clean = clean_text(original)
        opt_clean = clean_text(optimized)
        
        # 如果清理后的文本完全相同，说明保持了原始含义
        if orig_clean == opt_clean:
            return True
            
        # 如果优化后的文本完全改变了原始文本，返回False
        if len(orig_clean) < 5 and orig_clean not in opt_clean:
            return False
            
        # 计算文本相似度
        similarity = len(set(orig_clean) & set(opt_clean)) / len(set(orig_clean) | set(opt_clean))
        
        # 如果相似度低于0.5，认为含义发生了显著改变
        return similarity >= 0.5

    def _extract_variables(self, content: str) -> List[str]:
        """从内容中提取变量名"""
        pattern = r'\{([^}]+)\}'
        return list(set(re.findall(pattern, content))) 