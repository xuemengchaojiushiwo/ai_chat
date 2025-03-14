from typing import List
from ..knowledge.dataset import DocumentSegment

class PromptBuilder:
    @staticmethod
    def build_rag_prompt(query: str, relevant_segments: List[DocumentSegment]) -> str:
        """构建包含知识库内容的prompt"""
        # 1. 构建上下文部分
        context_parts = []
        for i, segment in enumerate(relevant_segments, 1):
            context_parts.append(
                f"[{i}] From document '{segment.document.name}':\n{segment.content}"
            )
        context = "\n\n".join(context_parts)
        
        # 2. 构建完整prompt
        prompt = f"""请基于以下参考资料回答问题。如果答案中使用了参考资料的内容，请在回答末尾注明引用的来源编号。

参考资料：
{context}

问题：{query}

请用中文回答。如果参考资料中没有相关信息，请诚实地说明。回答要简洁、准确。"""
        
        return prompt 