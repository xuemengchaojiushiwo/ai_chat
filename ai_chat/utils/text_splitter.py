from typing import List, Optional
import re

class TextSplitter:
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        
    def split_text(self, text: str) -> List[str]:
        """
        将文本分割成小段
        """
        # 预处理文本
        text = self._preprocess_text(text)
        return split_text(text, self.chunk_size, self.chunk_overlap)
        
    def _preprocess_text(self, text: str) -> str:
        """
        预处理文本，清理无用字符
        """
        # 替换多个空格为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 清理特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?，。！？]', '', text)
        return text.strip()

# 创建默认分割器实例
default_splitter = TextSplitter()

def split_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    将文本分割成小段
    
    Args:
        text: 要分割的文本
        chunk_size: 每段的最大字符数
        overlap: 相邻段落之间的重叠字符数
    
    Returns:
        分割后的文本段落列表
    """
    # 按段落分割
    paragraphs = text.split('\n\n')
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        # 如果段落太长，进一步分割
        if len(para) > chunk_size:
            words = para.split()
            for word in words:
                if current_size + len(word) + 1 > chunk_size:
                    # 保存当前块
                    if current_chunk:
                        chunks.append(' '.join(current_chunk))
                    # 开始新的块，包含一些重叠内容
                    overlap_size = 0
                    overlap_words = []
                    for prev_word in reversed(current_chunk):
                        if overlap_size + len(prev_word) + 1 > overlap:
                            break
                        overlap_words.insert(0, prev_word)
                        overlap_size += len(prev_word) + 1
                    current_chunk = overlap_words + [word]
                    current_size = sum(len(w) + 1 for w in current_chunk)
                else:
                    current_chunk.append(word)
                    current_size += len(word) + 1
        else:
            # 如果添加整个段落会超出大小限制
            if current_size + len(para) + 2 > chunk_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [para]
                current_size = len(para)
            else:
                if current_chunk:
                    current_chunk.append('')  # 添加段落分隔符
                current_chunk.append(para)
                current_size += len(para) + 2
    
    # 添加最后一个块
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

__all__ = ['TextSplitter', 'split_text'] 