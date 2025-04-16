import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Dict
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .conversation import ConversationManager
from .llm_factory import LLMFactory
from ..knowledge.retriever import Retriever
# SQLAlchemy models
from ..models.dataset import Conversation as DBConversation, Message
from ..models.document import DocumentSegment
# Pydantic models
from ..models.types import (
    MessageCreate,
    ConversationResponse,
    MessageResponse
)

logger = logging.getLogger(__name__)

class RetrievalConfig:
    """检索配置"""
    def __init__(self, 
                 top_k: int = 3,
                 score_threshold: float = 0.3,  # 降低相似度阈值，提高召回率
                 reranking_enabled: bool = False):
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.reranking_enabled = reranking_enabled

class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.retriever = Retriever(db)
        self.llm = None
        self.default_retrieval_config = RetrievalConfig()
        self.logger = logger
    
    @asynccontextmanager
    async def session(self):
        """Provide an async session context"""
        session = AsyncSession(self.db.bind)
        try:
            yield session
        finally:
            await session.close()

    async def get_conversations(self) -> List[DBConversation]:
        """获取所有对话列表"""
        try:
            result = await self.db.execute(
                select(DBConversation).order_by(DBConversation.created_at.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get conversations: {str(e)}")
            raise

    async def get_conversation(self, conversation_id: int) -> Optional[ConversationResponse]:
        """获取单个对话"""
        result = await self.db.execute(
            select(DBConversation).filter(DBConversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        return ConversationResponse.from_orm(conversation) if conversation else None

    async def create_conversation(self, name: str, workspace_id: int) -> DBConversation:
        """创建新对话"""
        logger.info(f"Creating conversation with name: {name} and workspace_id: {workspace_id}")
        try:
            # 获取AI回复和标题（合并为一次LLM调用）
            logger.info(f"Getting AI response for: {name}")
            llm = LLMFactory.create_llm()
            
            # 根据 workspace_id 决定是否使用 RAG
            system_prompt = "你是一个有帮助的AI助手。请根据用户的问题提供准确、相关和有帮助的回答。"
            relevant_docs = []
            if workspace_id > 0:
                # 如果 workspace_id > 0，使用 RAG
                relevant_docs = await self.retriever.search_with_embedding(
                    name,
                    limit=self.default_retrieval_config.top_k,
                    workspace_id=workspace_id
                )
                processed_docs = await self.process_retrieved_documents(relevant_docs, name)
                system_prompt = self._build_system_prompt(processed_docs)
                logger.info("Using RAG for conversation creation")
            else:
                logger.info("Creating conversation without RAG (workspace_id = 0)")

            # 修改系统提示以包含生成标题的请求
            enhanced_system_prompt = system_prompt + "\n\n同时，请在回复的最后一行单独添加一行，格式为：\n###TITLE:简短的对话标题\n这个标题应该不超过20个字，不包含标点符号，概括对话主题。这一行不会显示给用户。"

            ai_response = await llm.chat(
                system=enhanced_system_prompt,
                history=[],
                message=name
            )
            logger.info(f"Got AI response: {ai_response[:50]}...")

            # 提取标题和实际回复
            title = name[:20]  # 默认标题，使用提问的前20个字符
            response_content = ai_response
            
            # 检查是否包含标题标记
            if "###TITLE:" in ai_response:
                parts = ai_response.split("###TITLE:")
                response_content = parts[0].strip()
                if len(parts) > 1:
                    title = parts[1].strip()[:20]
                    logger.info(f"Extracted title: {title}")
            
            # 提取实际使用的引用
            citations = await self._extract_used_citations(response_content, relevant_docs) if relevant_docs else []

            # 创建对话
            conversation = DBConversation(
                title=title,
                workspace_id=workspace_id,
                created_at=datetime.utcnow()
            )
            self.db.add(conversation)
            await self.db.commit()
            await self.db.refresh(conversation)
            
            # 添加用户消息
            user_message = Message(
                conversation_id=conversation.id,
                content=name,
                role="user",
                created_at=datetime.utcnow()
            )
            self.db.add(user_message)

            # 添加AI回复消息
            assistant_message = Message(
                conversation_id=conversation.id,
                content=response_content,
                role="assistant",
                created_at=datetime.utcnow(),
                citations=citations
            )
            self.db.add(assistant_message)
            
            await self.db.commit()
            
            return conversation

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating conversation: {str(e)}")
            raise Exception(f"创建对话时出错: {str(e)}")

    async def generate_title(self, user_message: str, ai_response: str) -> str:
        """生成对话标题"""
        try:
            # 构建提示词
            prompt = f"""请根据以下对话生成一个简短、有意义的标题（不超过20个字）：

用户：{user_message}
AI：{ai_response}

要求：
1. 标题要简洁明了，不超过20个字
2. 标题要能概括对话的主要内容
3. 不要使用标点符号
4. 不要使用"对话"、"聊天"等词
5. 直接返回标题，不要其他内容

标题："""

            # 调用AI服务生成标题
            llm = LLMFactory.create_llm()
            title = await llm.chat(
                system="你是一个标题生成助手。请根据对话内容生成简短、有意义的标题。",
                history=[],
                message=prompt
            )
            
            # 清理标题
            title = title.strip()
            if len(title) > 20:
                title = title[:20]
            
            return title
        except Exception as e:
            logger.error(f"Error generating title: {str(e)}")
            # 如果生成标题失败，使用用户消息的前20个字符
            return user_message[:20] if user_message else "新对话"

    async def create_message(self, message: MessageCreate) -> MessageResponse:
        """创建新消息"""
        db_message = Message(
            conversation_id=message.conversation_id,
            content=message.content,
            role=message.role,
            created_at=datetime.utcnow()
        )
        self.db.add(db_message)
        await self.db.commit()
        await self.db.refresh(db_message)
        return MessageResponse.from_orm(db_message)

    async def get_messages(self, conversation_id: int) -> List[Message]:
        """获取对话消息历史"""
        try:
            result = await self.db.execute(
                select(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            messages = result.scalars().all()

            # 处理每条消息的引用信息
            for message in messages:
                if message.citations:
                    # 确保 citations 是列表
                    if isinstance(message.citations, str):
                        message.citations = json.loads(message.citations)
                    
                    # 查询每个引用的文档片段位置信息
                    for citation in message.citations:
                        if 'segment_id' in citation:
                            segment_result = await self.db.execute(
                                select(DocumentSegment)
                                .filter(DocumentSegment.id == citation['segment_id'])
                            )
                            segment = segment_result.scalar_one_or_none()
                            if segment:
                                citation.update({
                                    'page_number': segment.page_number,
                                    'bbox_x': segment.bbox_x,
                                    'bbox_y': segment.bbox_y,
                                    'bbox_width': segment.bbox_width,
                                    'bbox_height': segment.bbox_height
                                })

            return messages
        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}")
            raise

    async def process_retrieved_documents(self, docs: List[Dict], query: str) -> List[Dict]:
        """处理检索到的文档"""
        logger.info(f"Processing {len(docs)} retrieved documents with threshold {self.default_retrieval_config.score_threshold}")
        
        processed_docs = []
        for doc in docs:
            # 使用文档中已有的相似度分数
            score = doc.get('similarity', 0)
            doc_id = doc.get('document_id', 'unknown')
            segment_id = doc.get('segment_id', 'unknown')
            
            # 记录每个文档的相似度
            logger.info(f"Document {doc_id} segment {segment_id} similarity: {score:.4f}")
            
            if score > self.default_retrieval_config.score_threshold:
                logger.info(f"Document {doc_id} segment {segment_id} accepted: similarity {score:.4f} > threshold {self.default_retrieval_config.score_threshold}")
                processed_docs.append(doc)
            else:
                logger.info(f"Document {doc_id} segment {segment_id} rejected: similarity {score:.4f} <= threshold {self.default_retrieval_config.score_threshold}")
        
        # 按相似度排序
        processed_docs.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        # 记录最终处理结果
        logger.info(f"Processed to {len(processed_docs)} relevant documents")
        for doc in processed_docs:
            logger.info(f"Final document - ID: {doc.get('document_id')}, Segment: {doc.get('segment_id')}, "
                       f"Similarity: {doc.get('similarity', 0):.4f}")
            logger.info(f"Content preview: {doc.get('content', '')[:100]}...")
        
        return processed_docs[:self.default_retrieval_config.top_k]

    def _build_system_prompt(self, relevant_docs: List[Dict]) -> str:
        """构建系统提示词"""
        if not relevant_docs:
            return "你是一个AI助手，请基于你的知识回答用户的问题。"
        
        # 构建知识库内容
        knowledge_base = "\n\n".join([
            f"[{i+1}] {doc.get('content', '')}"
            for i, doc in enumerate(relevant_docs)
        ])
        
        return f"""你是一个AI助手。我会给你一些相关的文档片段作为背景知识。请基于这些知识回答用户的问题。

背景知识：
{knowledge_base}

回答要求：
1. 如果你使用了背景知识中的内容，请在回答中使用引用标记，例如 [1]、[2] 等，对应上面的文档编号
2. 只在确实使用了某个文档的内容时才标注引用
3. 不要在回答中重复完整的文档内容，只需要用你的话总结或解释
4. 如果背景知识不足以回答问题，请基于你自己的知识回答，无需标注引用
5. 引用标记要放在相关内容的末尾，例如："根据分析，该产品的核心功能包括多模态输入支持[1]和实时数据处理[2]"
6. 在回答的最后，请添加一个新行并使用 ###CITATIONS: 标记，后面跟上你实际引用的文档编号数组，例如：
   ###CITATIONS: [1,2]

请开始回答用户的问题。"""

    async def _extract_used_citations(self, response: str, relevant_docs: List[Dict]) -> List[Dict]:
        """从回答中提取实际使用的引用"""
        used_citations = []
        
        # 查找 ###CITATIONS: 标记后的引用数组
        if "###CITATIONS:" in response:
            try:
                citations_text = response.split("###CITATIONS:")[-1].strip()
                # 解析JSON数组
                indices = json.loads(citations_text)
                
                # 获取引用的文档
                for index in indices:
                    if 1 <= index <= len(relevant_docs):  # 确保引用索引有效
                        doc = relevant_docs[index-1]
                        citation = {
                            "text": doc.get('content', ''),
                            "document_id": doc.get('document_id', ''),
                            "segment_id": doc.get('segment_id', ''),
                            "similarity": doc.get('similarity', 0),
                            "index": index,
                            "page_number": doc.get('page_number'),
                            "bbox_x": doc.get('bbox_x'),
                            "bbox_y": doc.get('bbox_y'),
                            "bbox_width": doc.get('bbox_width'),
                            "bbox_height": doc.get('bbox_height')
                        }
                        used_citations.append(citation)
            except json.JSONDecodeError:
                logger.warning("Failed to parse citations array, no citations will be included")
                
        return used_citations

    async def send_message(self, conversation_id: int, message_content: str, use_rag: bool = True) -> Message:
        """发送消息并获取回复"""
        try:
            # 创建用户消息
            user_message = Message(
                conversation_id=conversation_id,
                content=message_content,
                role="user",
                created_at=datetime.utcnow()
            )
            self.db.add(user_message)
            await self.db.commit()
            await self.db.refresh(user_message)

            # 获取并处理相关文档
            relevant_docs = []
            if use_rag:
                # 获取对话实例及其工作空间ID
                result = await self.db.execute(
                    select(DBConversation)
                    .filter(DBConversation.id == conversation_id)
                )
                conversation = result.scalar_one_or_none()
                workspace_id = conversation.workspace_id if conversation else None
                
                logger.info(f"Processing message for conversation {conversation_id} in workspace {workspace_id}")

                if workspace_id:
                    # 从工作空间关联的文档中检索
                    raw_docs = await self.retriever.search_with_embedding(
                        message_content, 
                        limit=self.default_retrieval_config.top_k,
                        workspace_id=workspace_id
                    )
                    logger.info(f"Retrieved {len(raw_docs)} raw documents from workspace {workspace_id}")
                    for doc in raw_docs:
                        logger.info(f"Document content preview: {doc['content'][:100]}...")
                    
                    relevant_docs = await self.process_retrieved_documents(raw_docs, message_content)
                    logger.info(f"Processed to {len(relevant_docs)} relevant documents")
                else:
                    logger.warning(f"Conversation {conversation_id} has no workspace associated")

            # 构建系统提示
            system_prompt = self._build_system_prompt(relevant_docs)

            # 获取对话历史并使用 ConversationManager 处理
            history_result = await self.get_messages(conversation_id)
            conversation_manager = ConversationManager()
            messages = [{"role": msg.role, "content": msg.content} for msg in history_result]
            preserved_messages = conversation_manager.prepare_messages(messages)
            history = [(msg["role"], msg["content"]) for msg in preserved_messages]
            
            logger.info(f"Using {len(history)} messages from history within token limit")
            
            # 调用 LLM
            llm = LLMFactory.create_llm()
            response = await llm.chat(
                system=system_prompt,
                history=history,
                message=message_content
            )

            # 清理响应内容，移除citations标记
            clean_response = response.split("###CITATIONS:")[0].strip() if "###CITATIONS:" in response else response

            # 提取实际使用的引用
            citations = await self._extract_used_citations(response, relevant_docs) if relevant_docs else []

            # 创建助手回复消息
            assistant_message = Message(
                conversation_id=conversation_id,
                content=clean_response,  # 使用清理后的响应
                role="assistant",
                created_at=datetime.utcnow(),
                citations=citations
            )
            self.db.add(assistant_message)
            await self.db.commit()
            await self.db.refresh(assistant_message)

            return assistant_message

        except Exception as e:
            logger.error(f"Error in send_message: {str(e)}")
            raise

    async def delete_conversation(self, conversation_id: int) -> bool:
        """删除对话及其所有消息"""
        try:
            # 首先检查对话是否存在
            result = await self.db.execute(
                select(DBConversation).filter(DBConversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                return False
                
            # 删除对话及其关联的消息（依赖于数据库的级联删除）
            await self.db.delete(conversation)
            await self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
            await self.db.rollback()
            raise 