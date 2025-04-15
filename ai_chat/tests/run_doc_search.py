import asyncio
import json
import logging

import numpy as np
from sqlalchemy import select

from ..database import get_db, engine
from ..models.document import Document, DocumentSegment
from ..services.vector_store import vector_store
from ..utils.embeddings import EmbeddingFactory

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 降低SQLAlchemy日志级别，避免过多输出
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

async def search_document_segments(document_id=None):
    """查询文档段落内容"""
    db = None
    try:
        async for session in get_db():
            db = session
            try:
                if document_id is not None:
                    # 查询指定文档
                    result = await session.execute(
                        select(Document).filter(Document.id == document_id)
                    )
                    document = result.scalar_one_or_none()
                    if not document:
                        logger.error(f"未找到ID为 {document_id} 的文档")
                        return
                    documents = [document]
                else:
                    # 查询所有文档
                    result = await session.execute(
                        select(Document)
                    )
                    documents = result.scalars().all()
                
                logger.info(f"\nFound {len(documents)} documents:")
                
                for doc in documents:
                    logger.info(f"\nDocument ID: {doc.id}")
                    logger.info(f"Name: {doc.name}")
                    
                    # 查询该文档的所有段落
                    result = await session.execute(
                        select(DocumentSegment)
                        .filter(DocumentSegment.document_id == doc.id)
                        .order_by(DocumentSegment.position)
                    )
                    segments = result.scalars().all()
                    
                    logger.info(f"Found {len(segments)} segments:")
                    for i, segment in enumerate(segments, 1):
                        logger.info(f"\nSegment {i}:")
                        logger.info(f"ID: {segment.id}")
                        logger.info(f"Position: {segment.position}")
                        logger.info(f"Page: {segment.page_number}")
                        logger.info(f"Content: {segment.content[:200]}...")
                        logger.info(f"Chroma ID: {segment.chroma_id}")
                        
                        # 检查段落是否有 embedding
                        has_embedding = False
                        try:
                            if segment.embedding:
                                embedding_data = json.loads(segment.embedding)
                                has_embedding = len(embedding_data) > 0
                                logger.info(f"Embedding: 有 ({len(embedding_data)} 维)")
                            else:
                                logger.warning(f"Embedding: 没有")
                        except:
                            logger.warning(f"Embedding: 格式错误")
            except Exception as e:
                logger.error(f"查询文档时发生错误: {str(e)}")
                raise
    finally:
        if db:
            await db.close()

async def check_all_chroma_data():
    """检查所有 Chroma 数据"""
    try:
        # 获取集合中的所有数据
        all_data = vector_store.collection.get()
        
        logger.info("---------- Chroma 数据库统计信息 ----------")
        logger.info(f"总文档数量: {len(all_data['ids'])}")
        
        # 检查数据结构
        logger.info(f"数据结构: {list(all_data.keys())}")
        
        # 详细检查元数据
        if 'metadatas' in all_data and all_data['metadatas']:
            logger.info(f"元数据示例 (前3个):")
            for i in range(min(3, len(all_data['metadatas']))):
                logger.info(f"  ID {all_data['ids'][i]} 元数据: {all_data['metadatas'][i]}")
        
        # 检查 document_id 为 37 的数据
        doc_37_ids = [id for id in all_data['ids'] if id.startswith('doc_37_')]
        logger.info(f"文档 37 在 Chroma 中的段落数: {len(doc_37_ids)}")
        if doc_37_ids:
            logger.info(f"文档 37 的 Chroma IDs: {doc_37_ids}")
            
            # 详细检查文档37的元数据
            for id in doc_37_ids[:3]:  # 只显示前3个
                idx = all_data['ids'].index(id)
                logger.info(f"ID {id} 元数据: {all_data['metadatas'][idx] if 'metadatas' in all_data and all_data['metadatas'] else '无'}")
                
            # 检查这些 ID 是否有 embeddings
            for id in doc_37_ids:
                idx = all_data['ids'].index(id)
                has_embedding = 'embeddings' in all_data and len(all_data['embeddings']) > idx
                if has_embedding:
                    emb = all_data['embeddings'][idx]
                    logger.info(f"ID {id} 有 embedding: {len(emb) if emb else '无'}")
                else:
                    logger.warning(f"ID {id} 没有 embedding")
        
        # 随机显示几个示例
        if len(all_data['ids']) > 0:
            sample_size = min(5, len(all_data['ids']))
            indices = np.random.choice(len(all_data['ids']), sample_size, replace=False)
            
            logger.info(f"\n随机 {sample_size} 个样本:")
            for i in indices:
                logger.info(f"ID: {all_data['ids'][i]}")
                if 'metadatas' in all_data and all_data['metadatas']:
                    logger.info(f"元数据: {all_data['metadatas'][i]}")
                if 'embeddings' in all_data and all_data['embeddings']:
                    emb = all_data['embeddings'][i]
                    logger.info(f"Embedding 长度: {len(emb) if emb else '无'}")
        
        logger.info("------------------------------------------")
        
        return all_data
    except Exception as e:
        logger.error(f"检查 Chroma 数据时出错: {str(e)}")
        return None

async def check_chroma_query(query_embedding, segment_ids=None):
    """测试 Chroma 查询，不使用过滤器"""
    logger.info("执行 Chroma 无过滤查询测试...")
    try:
        # 不带过滤器的查询
        results_no_filter = vector_store.collection.query(
            query_embeddings=[query_embedding],
            n_results=20,
            include=["metadatas", "distances", "documents"]
        )
        
        logger.info("----------- 无过滤条件的 Chroma 结果 -----------")
        if results_no_filter.get("ids") and results_no_filter["ids"][0]:
            logger.info(f"查询返回 {len(results_no_filter['ids'][0])} 条结果")
            for i, (doc_id, distance) in enumerate(zip(
                results_no_filter["ids"][0],
                results_no_filter["distances"][0]
            )):
                similarity = 1 - (distance / 2)
                logger.info(f"结果 {i+1}: ID={doc_id}, 距离={distance:.4f}, 相似度={similarity:.4f}")
                
                # 检查是否是目标文档的段落
                is_target = False
                if segment_ids and doc_id in segment_ids:
                    is_target = True
                    logger.info(f"  [目标文档段落]")
        else:
            logger.info("无过滤查询也没有返回结果，这很奇怪")
        logger.info("---------------------------------------------")
        
        return results_no_filter
    except Exception as e:
        logger.error(f"无过滤器查询出错: {str(e)}")
        return None

async def search_similarity(document_id=None):
    """相似度搜索"""
    db = None
    try:
        async for session in get_db():
            db = session
            try:
                # 检查 Chroma 数据库状态
                await check_all_chroma_data()
                
                # 测试查询
                test_queries = [
                    "十大主要投资关键词"
                ]
                
                # 创建embedding工厂
                embedding_factory = EmbeddingFactory()
                
                # 如果指定了文档ID，构建where条件
                where_filter = None
                if document_id is not None:
                    # 使用document_id过滤方式
                    where_filter = {"document_id": str(document_id)}
                    logger.info(f"使用document_id过滤条件: {where_filter}")
                    logger.info(f"查询文档 {document_id} 的所有段落")
                else:
                    logger.info("未指定文档ID，将查询所有文档")
                
                for query in test_queries:
                    logger.info(f"\n测试查询: {query}")
                    
                    # 生成查询的embedding
                    logger.info("生成查询的embedding...")
                    embeddings_result = await embedding_factory.get_embeddings(query)
                    
                    # 确保我们获取的是单一向量 (取第一个嵌套列表)
                    if isinstance(embeddings_result, list):
                        if len(embeddings_result) > 0:
                            # 如果是嵌套列表，使用第一个
                            if isinstance(embeddings_result[0], list):
                                query_embedding = embeddings_result[0]
                            else:
                                query_embedding = embeddings_result
                        else:
                            logger.error("获取到空的embedding结果")
                            continue
                    else:
                        query_embedding = embeddings_result
                    
                    # 确保 query_embedding 是有效的数值数组
                    if not all(isinstance(x, (int, float)) for x in query_embedding):
                        logger.error(f"embedding包含非数值元素: {type(query_embedding[0])}")
                        continue
                    
                    logger.info(f"embedding长度: {len(query_embedding)}")
                    
                    # 测试无过滤条件的查询
                    logger.info("\n执行无过滤条件查询...")
                    no_filter_results = vector_store.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=20,
                        include=["metadatas", "distances", "documents"]
                    )
                    
                    # 显示结果
                    if no_filter_results.get("ids") and no_filter_results["ids"][0]:
                        logger.info(f"无过滤查询返回 {len(no_filter_results['ids'][0])} 条结果")
                        # 显示前5条结果
                        for i in range(min(5, len(no_filter_results['ids'][0]))):
                            doc_id = no_filter_results['ids'][0][i]
                            distance = no_filter_results['distances'][0][i]
                            similarity = 1 - (distance / 2)
                            logger.info(f"  结果 {i+1}: ID={doc_id}, 相似度={similarity:.4f}")
                    
                    # 如果有文档ID，使用document_id过滤查询
                    if where_filter:
                        logger.info(f"\n使用document_id={document_id}过滤查询...")
                        try:
                            filtered_results = vector_store.collection.query(
                                query_embeddings=[query_embedding],
                                n_results=20,
                                where=where_filter,
                                include=["metadatas", "distances", "documents"]
                            )
                            
                            # 检查过滤结果
                            if filtered_results.get("ids") and filtered_results["ids"][0]:
                                logger.info(f"过滤查询返回 {len(filtered_results['ids'][0])} 条结果")
                                # 显示前5条结果
                                for i in range(min(5, len(filtered_results['ids'][0]))):
                                    doc_id = filtered_results['ids'][0][i]
                                    distance = filtered_results['distances'][0][i]
                                    similarity = 1 - (distance / 2)
                                    logger.info(f"  结果 {i+1}: ID={doc_id}, 相似度={similarity:.4f}")
                                    
                                    # 获取内容预览
                                    if 'documents' in filtered_results and filtered_results['documents'][0]:
                                        content_preview = filtered_results['documents'][0][i][:100] + "..."
                                        logger.info(f"  内容: {content_preview}")
                            else:
                                logger.warning("过滤查询没有返回结果")
                        except Exception as e:
                            logger.error(f"过滤查询出错: {str(e)}")
            except Exception as e:
                logger.error(f"相似度搜索时发生错误: {str(e)}")
                raise
    finally:
        if db:
            await db.close()

async def direct_chroma_query(document_id=None):
    """直接使用Chroma API测试不同查询方法"""
    logger.info("\n开始直接使用Chroma API测试查询...")
    
    try:
        # 获取所有数据
        all_data = vector_store.collection.get()
        logger.info(f"Chroma中共有 {len(all_data['ids'])} 条数据")
        
        # 寻找特定文档的段落
        doc_specific_ids = [id for id in all_data['ids'] if f"doc_{document_id}_" in id]
        logger.info(f"找到与文档 {document_id} 相关的 {len(doc_specific_ids)} 个段落: {doc_specific_ids}")
        
        if doc_specific_ids:
            # 直接通过ID获取
            logger.info("\n测试方法1: 直接通过ID获取特定文档")
            try:
                get_result = vector_store.collection.get(ids=doc_specific_ids)
                logger.info(f"成功获取到 {len(get_result['ids'])} 个段落")
                for i in range(min(3, len(get_result['ids']))):
                    logger.info(f"  ID: {get_result['ids'][i]}")
                    if 'documents' in get_result and get_result['documents']:
                        logger.info(f"  内容: {get_result['documents'][i][:100]}...")
            except Exception as e:
                logger.error(f"通过ID获取失败: {str(e)}")
    except Exception as e:
        logger.error(f"直接查询出错: {str(e)}")

async def main(doc_id=None):
    """主函数"""
    if doc_id and not isinstance(doc_id, int):
        try:
            doc_id = int(doc_id)
        except ValueError:
            logger.error("文档ID必须是一个整数")
            return
    
    logger.info("开始查询文档段落...")
    await search_document_segments(doc_id)
    
    # 添加直接 Chroma 查询测试
    if doc_id:
        await direct_chroma_query(doc_id)
    
    logger.info("\n\n开始相似度搜索...")
    await search_similarity(doc_id)
    
    # 确保所有连接正确关闭
    await engine.dispose()

if __name__ == "__main__":
    import sys
    
    # 获取命令行参数中的文档ID
    doc_id = None
    if len(sys.argv) > 1:
        doc_id = sys.argv[1]
        logger.info(f"将在文档 {doc_id} 中进行搜索")
    
    # 运行主函数
    try:
        asyncio.run(main(doc_id))
    except KeyboardInterrupt:
        logger.info("用户中断执行")
    except Exception as e:
        logger.error(f"执行时出现错误: {str(e)}")
    finally:
        logger.info("程序执行完毕") 