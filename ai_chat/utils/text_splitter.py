from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import re

@dataclass
class TextBlock:
    """文本块数据类"""
    text: str
    page_number: int
    block_type: str  # 'text', 'table', 'list', 'title', etc.
    position: Dict[str, float]  # 位置信息，包含 x0, y0, x1, y1
    metadata: Dict[str, Any]  # 额外元数据

class TextSplitter:
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化文本分割器
        
        Args:
            config: 配置字典，如果为None则使用默认配置
        """
        default_config = {
            'max_segment_length': 500,
            'overlap_length': 50,
            'min_segment_length': 100
        }
        self.config = config or default_config
        self.max_length = self.config['max_segment_length']
        self.overlap = self.config['overlap_length']
        self.min_length = self.config['min_segment_length']
    
    def split_blocks(self, blocks: List[TextBlock]) -> List[Dict]:
        """智能分割文本块"""
        segments = []
        current_segment = []
        current_length = 0
        
        for block in blocks:
            # 1. 特殊块类型处理
            if block.block_type in ['table', 'title']:
                # 处理当前段落
                if current_segment:
                    segments.extend(self._finalize_segment(current_segment))
                    current_segment = []
                    current_length = 0
                
                # 添加特殊块
                segments.append({
                    'text': block.text,
                    'type': block.block_type,
                    'page_number': block.page_number,
                    'metadata': {
                        **block.metadata,
                        'position': block.position
                    }
                })
                continue
            
            # 2. 处理普通文本块
            block_length = len(block.text)
            
            # 如果当前块太长，需要分割
            if block_length > self.max_length:
                # 处理当前段落
                if current_segment:
                    segments.extend(self._finalize_segment(current_segment))
                    current_segment = []
                    current_length = 0
                
                # 分割长块
                sub_segments = self._split_long_block(block)
                segments.extend(sub_segments)
                continue
            
            # 如果添加当前块会超出最大长度
            if current_length + block_length > self.max_length:
                # 完成当前段落
                segments.extend(self._finalize_segment(current_segment))
                current_segment = [block]
                current_length = block_length
            else:
                # 添加到当前段落
                current_segment.append(block)
                current_length += block_length
        
        # 处理最后的段落
        if current_segment:
            segments.extend(self._finalize_segment(current_segment))
        
        return segments
    
    def _split_long_block(self, block: TextBlock) -> List[Dict]:
        """分割长文本块"""
        text = block.text
        segments = []
        start = 0
        
        while start < len(text):
            # 找到合适的分割点
            end = start + self.max_length
            if end < len(text):
                # 尝试在句子边界分割
                sentence_end = self._find_sentence_boundary(text, end)
                if sentence_end > start + self.min_length:
                    end = sentence_end
            
            # 创建新的段落
            segment_text = text[start:end]
            segments.append({
                'text': segment_text,
                'type': 'text',
                'page_number': block.page_number,
                'metadata': {
                    **block.metadata,
                    'is_split': True,
                    'original_position': block.position
                }
            })
            
            # 更新起始位置，考虑重叠
            start = end - self.overlap
        
        return segments
    
    def _find_sentence_boundary(self, text: str, position: int) -> int:
        """找到最近的句子边界"""
        # 在position附近查找句号、问号、感叹号
        sentence_ends = ['.', '。', '!', '！', '?', '？']
        
        # 向后查找
        for i in range(position, min(position + 100, len(text))):
            if text[i] in sentence_ends:
                return i + 1
        
        # 向前查找
        for i in range(position - 1, max(position - 100, 0), -1):
            if text[i] in sentence_ends:
                return i + 1
        
        # 如果没找到句子边界，退而查找标点符号
        puncs = ['，', ',', '；', ';', '：', ':']
        
        # 向后查找
        for i in range(position, min(position + 50, len(text))):
            if text[i] in puncs:
                return i + 1
        
        # 如果实在找不到合适的分割点，就直接在position分割
        return position
    
    def _finalize_segment(self, blocks: List[TextBlock]) -> List[Dict]:
        """完成当前段落的处理"""
        if not blocks:
            return []
            
        # 合并块的文本
        text = ' '.join(block.text for block in blocks)
        
        # 如果文本太短，直接返回
        if len(text) < self.min_length:
            return [{
                'text': text,
                'type': 'text',
                'page_number': blocks[0].page_number,
                'metadata': {
                    'merged_blocks': len(blocks),
                    'original_positions': [block.position for block in blocks]
                }
            }]
        
        # 否则可能需要进一步分割
        if len(text) > self.max_length:
            return self._split_long_block(TextBlock(
                text=text,
                page_number=blocks[0].page_number,
                block_type='text',
                position=blocks[0].position,
                metadata={
                    'merged_blocks': len(blocks),
                    'original_positions': [block.position for block in blocks]
                }
            ))
        
        return [{
            'text': text,
            'type': 'text',
            'page_number': blocks[0].page_number,
            'metadata': {
                'merged_blocks': len(blocks),
                'original_positions': [block.position for block in blocks]
            }
        }]

# 使用默认配置创建分割器实例
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