import logging
import os
import re
from typing import Optional, Tuple, List, Dict, Any

import markdown
import pdfplumber
from docx import Document as DocxDocument  # 重命名以避免冲突

from .text_splitter import TextBlock

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.line_margin = 3  # 行间距容差
        self.char_margin = 2  # 字符间距容差
        
    def process_pdf(self, file_path: str) -> Tuple[str, List[TextBlock]]:
        """处理PDF文件，返回文本内容和结构化的文本块"""
        text_blocks = []
        full_text = ""
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # 1. 提取并处理表格
                    tables = self._extract_tables(page, page_num, file_path)
                    text_blocks.extend(tables)
                    
                    # 2. 提取文本元素
                    words = page.extract_words(
                        keep_blank_chars=True,
                        x_tolerance=self.char_margin,
                        y_tolerance=self.line_margin
                    )
                    
                    # 3. 处理文本块
                    text_elements = self._process_text_elements(words, page_num, page)
                    text_blocks.extend(text_elements)
                    
                    # 4. 更新全文
                    page_text = "\n".join(block.text for block in text_elements)
                    full_text += page_text + "\n\n"
                    
        except Exception as e:
            raise Exception(f"处理PDF文件时出错: {str(e)}")
            
        return full_text.strip(), text_blocks
    
    def _extract_tables(self, page, page_num, file_path: str) -> List[TextBlock]:
        """提取并处理表格"""
        text_blocks = []
        
        # 暂时禁用Camelot表格提取
        # try:
        #     # 使用多种表格提取方法
        #     tables = []
        #     try:
        #         # 首先尝试使用lattice模式
        #         lattice_tables = camelot.read_pdf(file_path, pages=str(page_num), flavor='lattice')
        #         tables.extend(lattice_tables)
        #         logger.info(f"使用lattice模式提取到 {len(lattice_tables)} 个表格")
        #     except Exception as e:
        #         logger.warning(f"lattice模式提取表格失败: {str(e)}")
                
        #     try:
        #         # 然后尝试使用stream模式
        #         stream_tables = camelot.read_pdf(file_path, pages=str(page_num), flavor='stream')
        #         tables.extend(stream_tables)
        #         logger.info(f"使用stream模式提取到 {len(stream_tables)} 个表格")
        #     except Exception as e:
        #         logger.warning(f"stream模式提取表格失败: {str(e)}")
                
        #     for table in tables:
        #         if table.df.empty:
        #             continue
                    
        #         try:
        #             # 将表格转换为文本形式
        #             table_data = table.df.values.tolist()
        #             if not table_data:
        #                 continue
                        
        #             # 清理表格数据
        #             cleaned_data = []
        #             for row in table_data:
        #                 cleaned_row = []
        #                 for cell in row:
        #                     # 清理单元格数据
        #                     if cell is None:
        #                         cell = ''
        #                     cell = str(cell).strip()
        #                     # 移除多余的空白字符
        #                     cell = ' '.join(cell.split())
        #                     cleaned_row.append(cell)
        #                 if any(cell for cell in cleaned_row):  # 只保留非空行
        #                     cleaned_data.append(cleaned_row)
                    
        #             if not cleaned_data:  # 如果清理后没有数据，跳过
        #                 continue
                        
        #             table_text = self._table_to_text(cleaned_data)
                    
        #             # 获取表格位置信息
        #             bbox = {
        #                 'x0': table.bbox[0],
        #                 'y0': table.bbox[1],
        #                 'x1': table.bbox[2],
        #                 'y1': table.bbox[3]
        #             }
                    
        #             # 确保正确获取行数和列数
        #             rows = len(cleaned_data)
        #             cols = len(cleaned_data[0]) if cleaned_data else 0
                    
        #             # 检查表格是否包含数字数据
        #             has_numbers = any(
        #                 any(cell.replace('.', '').replace('-', '').replace('%', '').isdigit()
        #                     for cell in row)
        #                 for row in cleaned_data
        #             )
                    
        #             # 检查表格是否包含日期数据
        #             has_dates = any(
        #                 any(re.search(r'\d{1,4}[-/年]\d{1,2}[-/月]\d{1,2}|'
        #                             r'\d{4}[-/]\d{1,2}|'
        #                             r'\d{1,2}[-/]\d{4}', cell)
        #                     for cell in row)
        #                 for row in cleaned_data
        #             )
                    
        #             table_block = TextBlock(
        #                 text=table_text,
        #                 page_number=table.page,
        #                 block_type='table',
        #                 position=bbox,
        #                 metadata={
        #                     'rows': rows,
        #                     'cols': cols,
        #                     'is_table': True,
        #                     'has_numbers': has_numbers,
        #                     'has_dates': has_dates,
        #                     'table_data': cleaned_data,
        #                     'bbox': bbox
        #                 }
        #             )
        #             text_blocks.append(table_block)
        #             logger.info(f"成功提取表格：{rows}行 x {cols}列")
        #             logger.info(f"表格预览：\n{table_text[:200]}...")
                    
        #         except Exception as e:
        #             logger.warning(f"处理表格时出错: {str(e)}")
        #             continue
                    
        # except Exception as e:
        #     logger.warning(f"使用Camelot提取表格时出错: {str(e)}")
                    
        return text_blocks
    
    def _process_text_elements(self, words, page_num, page) -> List[TextBlock]:
        """处理文本元素"""
        text_blocks = []
        current_line = []
        current_y = None
        
        # 按行分组并处理
        for word in sorted(words, key=lambda w: (w['top'], w['x0'])):
            if current_y is None:
                current_y = word['top']
                current_line.append(word)
            elif abs(word['top'] - current_y) <= self.line_margin:
                current_line.append(word)
            else:
                if current_line:
                    block = self._create_text_block(current_line, page_num, page)
                    if block:
                        text_blocks.append(block)
                current_y = word['top']
                current_line = [word]
        
        # 处理最后一行
        if current_line:
            block = self._create_text_block(current_line, page_num, page)
            if block:
                text_blocks.append(block)
        
        # 尝试识别表格结构
        try:
            # 按y坐标分组
            y_groups = {}
            for block in text_blocks:
                y = block.position['y0']
                if y not in y_groups:
                    y_groups[y] = []
                y_groups[y].append(block)
            
            # 对每行进行排序
            for y, blocks in y_groups.items():
                blocks.sort(key=lambda b: b.position['x0'])
                
                # 检查是否是表格行
                if len(blocks) > 1 and self._is_table_row(blocks):
                    for block in blocks:
                        block.block_type = 'table_cell'
                        block.metadata['is_table'] = True
                        block.metadata['row_y'] = y
        except Exception as e:
            logger.error(f"处理表格结构时出错: {str(e)}")
        
        return text_blocks
    
    def _is_table_row(self, blocks: List[TextBlock]) -> bool:
        """判断是否是表格行"""
        if len(blocks) < 2:
            return False
            
        # 检查是否有数字和日期
        has_numbers = False
        has_dates = False
        
        for block in blocks:
            text = block.text
            # 检查数字
            if re.search(r'\d+\.?\d*', text):
                has_numbers = True
            # 检查日期格式
            if re.search(r'\d{2}-\d{2}-\d{4}', text):
                has_dates = True
        
        # 检查对齐方式
        x_positions = [block.position['x0'] for block in blocks]
        x_diffs = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
        is_aligned = all(abs(diff - x_diffs[0]) < 10 for diff in x_diffs)
        
        return (has_numbers or has_dates) and is_aligned
    
    def _create_text_block(self, words, page_num, page) -> Optional[TextBlock]:
        """创建文本块"""
        if not words:
            return None
            
        # 提取文本
        text = ' '.join(w['text'] for w in words)
        
        # 计算位置信息
        position = {
            'x0': min(w['x0'] for w in words),
            'y0': min(w['top'] for w in words),
            'x1': max(w['x1'] for w in words),
            'y1': max(w['bottom'] for w in words)
        }
        
        # 判断块类型
        block_type = self._determine_block_type(text, words, page)
        
        # 创建元数据
        metadata = {
            'font_size': words[0].get('size', 0),
            'font_name': words[0].get('font', ''),
            'is_bold': any(w.get('bold', False) for w in words),
            'alignment': self._determine_alignment(position, page),
            'has_numbers': bool(re.search(r'\d+\.?\d*', text)),
            'has_dates': bool(re.search(r'\d{2}-\d{2}-\d{4}', text))
        }
        
        return TextBlock(
            text=text,
            page_number=page_num,
            block_type=block_type,
            position=position,
            metadata=metadata
        )
    
    def _determine_block_type(self, text: str, words: List[Dict], page) -> str:
        """确定文本块类型"""
        # 1. 检查是否为标题
        if self._is_title(text, words, page):
            return 'title'
            
        # 2. 检查是否为列表项
        if self._is_list_item(text):
            return 'list'
            
        # 3. 检查是否为表格单元格
        if self._is_table_cell(words, page):
            return 'table_cell'
            
        # 4. 默认为普通文本
        return 'text'
    
    def _is_title(self, text: str, words: List[Dict], page) -> bool:
        """判断是否为标题"""
        if not words:
            return False
            
        # 1. 检查字体大小
        avg_font_size = sum(w.get('size', 0) for w in words) / len(words)
        
        # 2. 检查是否加粗
        is_bold = any(w.get('bold', False) for w in words)
        
        # 3. 检查文本长度
        text_length = len(text.strip())
        
        # 4. 检查是否独占一行
        is_single_line = True  # 需要根据实际布局判断
        
        return (avg_font_size > 12 and  # 字体较大
                (is_bold or avg_font_size > 14) and  # 加粗或更大字体
                text_length < 200 and  # 长度适中
                is_single_line)  # 独占一行
    
    def _is_list_item(self, text: str) -> bool:
        """判断是否为列表项"""
        # 检查常见的列表标记
        list_patterns = [
            r'^\s*[\-\•\*]\s+',  # 无序列表
            r'^\s*\d+[\.\)]\s+',  # 有序列表
            r'^\s*[a-zA-Z][\.\)]\s+',  # 字母列表
        ]
        
        return any(re.match(pattern, text) for pattern in list_patterns)
    
    def _table_to_text(self, table: List[List[str]]) -> str:
        """将表格转换为文本形式"""
        if not table:
            return ""
            
        # 1. 清理单元格数据
        cleaned_table = [[str(cell).strip() if cell is not None else '' for cell in row] for row in table]
        
        # 2. 计算每列的最大宽度
        col_widths = [max(len(str(row[i])) for row in cleaned_table) for i in range(len(cleaned_table[0]))]
        
        # 3. 构建表格文本
        table_str = []
        for row in cleaned_table:
            row_str = " | ".join(str(cell).ljust(width) for cell, width in zip(row, col_widths))
            table_str.append(row_str)
            
        return "\n".join(table_str)
    
    def _determine_alignment(self, position: Dict, page) -> str:
        """确定文本对齐方式"""
        page_width = page.width
        x0, x1 = position['x0'], position['x1']
        
        # 简单的对齐判断逻辑
        if x0 < page_width * 0.2:
            return 'left'
        elif x1 > page_width * 0.8:
            return 'right'
        else:
            return 'center'
    
    def _is_table_cell(self, words: List[Dict], page) -> bool:
        """判断是否为表格单元格"""
        if not words:
            return False
            
        # 检查是否在表格区域内
        word_bbox = {
            'x0': min(w['x0'] for w in words),
            'y0': min(w['top'] for w in words),
            'x1': max(w['x1'] for w in words),
            'y1': max(w['bottom'] for w in words)
        }
        
        try:
            # 检查是否有表格线
            rects = page.rects
            if rects:
                for rect in rects:
                    # 获取矩形的边界框
                    if isinstance(rect, dict):
                        rect_bbox = {
                            'x0': rect.get('x0', 0),
                            'y0': rect.get('top', 0),
                            'x1': rect.get('x1', 0),
                            'y1': rect.get('bottom', 0)
                        }
                    elif hasattr(rect, 'bbox'):
                        rect_bbox = {
                            'x0': rect.bbox[0],
                            'y0': rect.bbox[1],
                            'x1': rect.bbox[2],
                            'y1': rect.bbox[3]
                        }
                    else:
                        continue
                    
                    # 如果文本在某个矩形内部，可能是表格单元格
                    if (rect_bbox['x0'] <= word_bbox['x0'] and
                        rect_bbox['y0'] <= word_bbox['y0'] and
                        rect_bbox['x1'] >= word_bbox['x1'] and
                        rect_bbox['y1'] >= word_bbox['y1']):
                        return True
        except AttributeError:
            pass
        
        # 检查是否有规则的对齐和间距（表格的特征）
        if len(words) > 1:
            # 检查垂直对齐
            tops = [w['top'] for w in words]
            if max(tops) - min(tops) < self.line_margin:
                # 检查水平间距是否规则
                x_gaps = []
                sorted_words = sorted(words, key=lambda w: w['x0'])
                for i in range(len(sorted_words) - 1):
                    gap = sorted_words[i + 1]['x0'] - sorted_words[i]['x1']
                    x_gaps.append(gap)
                
                # 如果间距比较规则，可能是表格单元格
                if x_gaps and max(x_gaps) - min(x_gaps) < self.char_margin:
                    return True
        
        return False

def process_file(file_path: str) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    处理不同类型的文件并提取文本内容
    返回: (文本内容, MIME类型, 文本块列表)
    """
    mime_type = get_mime_type(file_path)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    try:
        if mime_type == 'application/pdf':
            processor = PDFProcessor()
            content, text_blocks = processor.process_pdf(file_path)
            # 将TextBlock对象转换为字典
            blocks_dict = [
                {
                    'text': block.text,
                    'page_number': block.page_number,
                    'block_type': block.block_type,
                    'position': block.position,
                    'metadata': block.metadata
                }
                for block in text_blocks
            ]
            return content, mime_type, blocks_dict
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            content, text_blocks = process_docx(file_path)
            return content, mime_type, text_blocks
        elif mime_type == 'text/markdown' or file_path.endswith('.md'):
            content, text_blocks = process_markdown(file_path)
            return content, mime_type, text_blocks
        elif mime_type.startswith('text/'):
            content, text_blocks = process_text(file_path)
            return content, mime_type, text_blocks
        else:
            raise ValueError(f"不支持的文件类型: {mime_type}")
    except Exception as e:
        raise Exception(f"处理文件时出错: {str(e)}")

def process_docx(file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
    """处理 Word 文档"""
    text = ""
    try:
        doc = DocxDocument(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        raise Exception(f"处理 Word 文档时出错: {str(e)}")
    return text.strip(), []

def process_markdown(file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
    """处理 Markdown 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            # 转换 Markdown 为纯文本
            html = markdown.markdown(text)
            # TODO: 可以添加 HTML 到纯文本的转换
            return text, []
    except Exception as e:
        raise Exception(f"处理 Markdown 文件时出错: {str(e)}")

def process_text(file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
    """处理纯文本文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip(), []
    except Exception as e:
        raise Exception(f"处理文本文件时出错: {str(e)}") 

def get_mime_type(file_path: str) -> str:
    """根据文件扩展名获取MIME类型"""
    ext = os.path.splitext(file_path)[1].lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.md': 'text/markdown',
        '.txt': 'text/plain'
    }
    return mime_types.get(ext, 'application/octet-stream') 