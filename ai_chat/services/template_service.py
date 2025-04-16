import asyncio
import json
import logging
import re
import time
from collections import OrderedDict
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..api.schemas.template import (
    TemplateCreate,
    TemplateUse,
    TemplateUsageResponse,
    TemplateVariable
)
from ..chat.llm_factory import get_llm_service
from ..models.template import Template

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
            result = json.loads(text)
            # 确保variables中的每个变量都有required字段
            if "variables" in result:
                for var in result["variables"]:
                    if "required" not in var:
                        var["required"] = True  # 默认为True
            return result
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
                        timeout=60.0  # 60秒超时
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
                    template_name = template_data.description[:20]
                    
                    # 根据描述中的关键词生成更合适的模板内容
                    content = "模板内容 - 请编辑"
                    prompt_template = "<div>模板内容 - 请编辑</div>"
                    variables = []
                    
                    # 检查描述中是否包含特定关键词，并生成相应的模板
                    if "会议" in template_data.description:
                        content = """【会议通知】\n\n主题：{meeting_title}\n\n时间：{meeting_time}\n\n地点：{meeting_location}\n\n参会人员：{attendees}\n\n会议议程：\n{agenda}\n\n注意事项：\n1. 请准时参加\n2. 请提前准备相关材料\n3. 如有特殊情况请提前请假\n\n联系人：{contact_person}\n电话：{contact_phone}"""
                        prompt_template = f"<div>{content}</div>"
                        variables = [
                            {"name": "meeting_title", "description": "会议主题"},
                            {"name": "meeting_time", "description": "会议时间"},
                            {"name": "meeting_location", "description": "会议地点"},
                            {"name": "attendees", "description": "参会人员"},
                            {"name": "agenda", "description": "会议议程"},
                            {"name": "contact_person", "description": "联系人"},
                            {"name": "contact_phone", "description": "联系电话"}
                        ]
                    elif "活动" in template_data.description or "推广" in template_data.description:
                        content = """【活动通知】\n\n活动名称：{event_name}\n\n活动时间：{event_time}\n\n活动地点：{event_location}\n\n活动内容：\n{event_description}\n\n参与方式：{participation_method}\n\n注意事项：\n1. 请提前报名\n2. 请准时参加\n3. 如有疑问请联系我们\n\n联系人：{contact_person}\n电话：{contact_phone}"""
                        prompt_template = f"<div>{content}</div>"
                        variables = [
                            {"name": "event_name", "description": "活动名称"},
                            {"name": "event_time", "description": "活动时间"},
                            {"name": "event_location", "description": "活动地点"},
                            {"name": "event_description", "description": "活动内容"},
                            {"name": "participation_method", "description": "参与方式"},
                            {"name": "contact_person", "description": "联系人"},
                            {"name": "contact_phone", "description": "联系电话"}
                        ]
                    
                    result = {
                        "name": template_name,
                        "content": content,
                        "prompt_template": prompt_template,
                        "variables": variables,
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
            # 创建模板对象，确保variables中包含required字段
            processed_variables = []
            for var in result.get("variables", []):
                processed_variables.append({
                    "name": var["name"],
                    "description": var["description"],
                    "required": var.get("required", True)  # 默认为True
                })

            # 确保variables字段是一个有效的JSON对象
            variables_json = {
                "variables": processed_variables
            }

            db_template = Template(
                name=result.get("name", template_data.description[:20]),
                description=result.get("description", template_data.description),
                content=result.get("content", ""),
                prompt_template=result.get("prompt_template", ""),
                variables=variables_json,  # 使用完整的JSON对象
                category=result.get("category", "通用"),
                author=result.get("author", "AI助手"),
                style=result.get("style", "")
            )
            
            # 数据库操作前确认variables字段的格式
            logger.info(f"保存到数据库的variables字段: {db_template.variables}")
            
            # 数据库操作
            self.db.add(db_template)
            await self.db.commit()
            await self.db.refresh(db_template)
            
            # 验证保存后的数据
            saved_variables = db_template.variables.get("variables", [])
            for var in saved_variables:
                if "required" not in var:
                    logger.error(f"变量 {var['name']} 缺少required字段")
            
            # 构造响应
            response_data = {
                "id": db_template.id,
                "name": db_template.name,
                "description": db_template.description,
                "content": db_template.content,
                "prompt_template": db_template.prompt_template,
                "variables": saved_variables,  # 使用保存后的变量列表
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
            # 确保返回的变量列表中每个变量都有required字段
            variables = template.variables.get("variables", [])
            for var in variables:
                if "required" not in var:
                    var["required"] = True  # 添加默认值
            
            return {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "content": template.content,
                "prompt_template": template.prompt_template,
                "variables": variables,  # 返回处理后的变量列表
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

    async def update_template_variables(self, template_id: int, operation: str, variable: TemplateVariable, old_name: Optional[str] = None) -> Template:
        """更新模板变量 - 添加、删除或更新单个变量"""
        try:
            # 获取模板
            query = select(Template).where(Template.id == template_id)
            result = await self.db.execute(query)
            template = result.scalar_one_or_none()
            
            if not template:
                raise ValueError("Template not found")
            
            # 获取当前变量列表，确保是一个列表
            current_variables = template.variables.get("variables", []) if template.variables else []
            logger.info(f"当前变量列表: {current_variables}")
            
            if operation == "add":
                # 将 TemplateVariable 转换为字典，确保包含required字段
                new_variable = {
                    "name": variable.name,
                    "description": variable.description,
                    "required": variable.required if variable.required is not None else True
                }
                
                # 检查变量名是否已存在
                if any(var["name"] == variable.name for var in current_variables):
                    raise ValueError(f"Variable {variable.name} already exists")
                
                # 添加新变量
                current_variables.append(new_variable)
                logger.info(f"添加新变量: {new_variable}")
                
                # 更新模板中的变量列表
                new_variables = {
                    "variables": current_variables
                }
                
                # 使用 SQLAlchemy 更新
                stmt = (
                    update(Template)
                    .where(Template.id == template_id)
                    .values(
                        variables=new_variables,
                        version=template.version + 1,
                        updated_at=datetime.utcnow()
                    )
                )
                await self.db.execute(stmt)
                await self.db.commit()
                
                # 返回更新后的数据
                return {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "content": template.content,
                    "prompt_template": template.prompt_template,
                    "variables": current_variables,
                    "category": template.category,
                    "author": template.author,
                    "created_at": template.created_at,
                    "updated_at": datetime.utcnow(),
                    "version": template.version + 1,
                    "status": template.status,
                    "usage_count": template.usage_count
                }
                
            elif operation == "remove":
                # 删除指定名称的变量
                original_length = len(current_variables)
                # 使用传入的变量名进行删除
                target_name = variable.name
                current_variables = [
                    var for var in current_variables
                    if var["name"] != target_name
                ]
                if len(current_variables) == original_length:
                    raise ValueError(f"Variable {target_name} not found")
                logger.info(f"删除变量: {target_name}")
                
                # 更新模板中的变量列表
                new_variables = {
                    "variables": current_variables
                }
                
                # 使用 SQLAlchemy 更新
                stmt = (
                    update(Template)
                    .where(Template.id == template_id)
                    .values(
                        variables=new_variables,
                        version=template.version + 1,
                        updated_at=datetime.utcnow()
                    )
                )
                await self.db.execute(stmt)
                await self.db.commit()
                
                # 返回更新后的数据
                return {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "content": template.content,
                    "prompt_template": template.prompt_template,
                    "variables": current_variables,
                    "category": template.category,
                    "author": template.author,
                    "created_at": template.created_at,
                    "updated_at": datetime.utcnow(),
                    "version": template.version + 1,
                    "status": template.status,
                    "usage_count": template.usage_count
                }
                
            elif operation == "update":
                if not old_name:
                    raise ValueError("old_name is required for update operation")
                
                # 查找要更新的变量
                var_index = next((i for i, var in enumerate(current_variables) 
                                if var["name"] == old_name), -1)
                
                if var_index == -1:
                    raise ValueError(f"Variable {old_name} not found")
                
                # 如果变量名要改变，检查新名称是否已存在
                if variable.name != old_name and any(var["name"] == variable.name for var in current_variables):
                    raise ValueError(f"Variable name {variable.name} already exists")
                
                # 更新变量，使用新的required值
                current_variables[var_index] = {
                    "name": variable.name,
                    "description": variable.description,
                    "required": variable.required if variable.required is not None else True
                }
                
                # 如果变量名发生变化，更新模板内容中的引用
                new_content = template.content
                new_prompt_template = template.prompt_template
                if variable.name != old_name:
                    new_content = template.content.replace(
                        f"{{{old_name}}}", 
                        f"{{{variable.name}}}"
                    )
                    new_prompt_template = template.prompt_template.replace(
                        f"{{{old_name}}}", 
                        f"{{{variable.name}}}"
                    )
                
                logger.info(f"更新变量 {old_name} 为: {current_variables[var_index]}")
                
                # 更新模板中的变量列表
                new_variables = {
                    "variables": current_variables
                }
                
                # 使用 SQLAlchemy 更新
                stmt = (
                    update(Template)
                    .where(Template.id == template_id)
                    .values(
                        variables=new_variables,
                        content=new_content,
                        prompt_template=new_prompt_template,
                        version=template.version + 1,
                        updated_at=datetime.utcnow()
                    )
                )
                await self.db.execute(stmt)
                await self.db.commit()
                
                # 返回更新后的数据
                return {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "content": new_content,
                    "prompt_template": new_prompt_template,
                    "variables": current_variables,
                    "category": template.category,
                    "author": template.author,
                    "created_at": template.created_at,
                    "updated_at": datetime.utcnow(),
                    "version": template.version + 1,
                    "status": template.status,
                    "usage_count": template.usage_count
                }
            else:
                raise ValueError("Invalid operation. Must be 'add', 'remove', or 'update'")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新模板变量时出错: {str(e)}")
            raise ValueError(f"更新模板变量时出错: {str(e)}")

    async def use_template(self, template_id: int, template_use: TemplateUse) -> TemplateUsageResponse:
        """使用模板生成内容 - 性能优化版本"""
        start_time = time.time()
        logger.info(f"开始使用模板 {template_id} 生成内容")
        
        try:
            # 获取模板数据
            template_data = await self.get_template(template_id)
            if not template_data:
                raise ValueError("Template not found")
                
            # 获取模板变量定义
            variables = template_data["variables"]
            
            # 如果没有变量或所有变量都为空，直接使用原始值
            if not template_use.variable_values or all(not val for val in template_use.variable_values.values()):
                logger.info("跳过变量优化，使用原始值")
                optimized_values = template_use.variable_values
            else:
                # 构建包含所有变量的优化提示词
                variables_info = []
                for var_name, var_value in template_use.variable_values.items():
                    var_def = next((var for var in variables if var["name"] == var_name), None)
                    if var_def:
                        variables_info.append(f"""变量名：{var_name}
描述：{var_def["description"]}
当前值：{var_value}
---""")
                
                if variables_info:
                    # 修改LLM提示，使其更智能地优化用户输入
                    prompt = f"""请对以下模板变量值进行优化，在保持原意的基础上改善表达：

{chr(10).join(variables_info)}

优化规则：
1. 修正语法错误和标点符号使用
2. 统一日期格式为YYYY-MM-DD
3. 删除多余的标点符号
4. 优化语句通顺性
5. 保持用户原始表达的核心意图
6. 可以适当扩充语义，让表达更完整
7. 不要丢失关键信息
8. 对于空的变量，保持为空

示例：
输入：多日未见，，，。聚贤阁一句
优化后：多日未见，相约聚贤阁一聚

仅返回JSON格式：
{{
    "变量名1": "优化后的值1",
    "变量名2": "优化后的值2"
}}"""

                    try:
                        llm_start = time.time()
                        response = await asyncio.wait_for(
                            self.llm_service.chat(
                                system="你是一个专业的文本优化助手。你的任务是在保持原意的基础上，改善文本的表达，使其更加通顺、规范。",
                                history=[],
                                message=prompt
                            ),
                            timeout=20.0  # 20秒超时
                        )
                        logger.info(f"LLM响应时间: {time.time() - llm_start:.2f}秒")
                        
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
                    
            # 更高效的变量替换
            content = template_data["prompt_template"]
            # 预编译正则表达式
            var_pattern = re.compile(r'\{([^}]+)\}')
            # 一次性替换所有变量
            matches = var_pattern.findall(content)
            for var_name in matches:
                # 不管变量是否在 optimized_values 中都替换
                value = optimized_values.get(var_name, "")
                content = content.replace(f"{{{var_name}}}", value)
            
            # 清理多余的空行
            content = re.sub(r'\n\s*\n', '\n\n', content)
            content = content.strip()
            
            # 更新使用次数
            query = select(Template).where(Template.id == template_id)
            result = await self.db.execute(query)
            template = result.scalar_one_or_none()
            if template:
                template.usage_count += 1
                template.updated_at = datetime.utcnow()
                await self.db.commit()
            
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