import os
from docx import Document as DocxDocument  # 重命名以避免冲突
import pdfplumber
import markdown
from typing import Optional, Tuple, List, Dict, Any

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
            content, text_blocks = process_pdf(file_path)
            return content, mime_type, text_blocks
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

def process_pdf(file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
    """处理 PDF 文件，返回文本内容和文本块位置信息"""
    text = ""
    text_blocks = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # 提取文本和位置信息
                words = page.extract_words()
                
                # 按行分组单词
                current_line = []
                current_y = None
                line_margin = 3  # 允许的行高误差范围（像素）
                
                for word in words:
                    if current_y is None:
                        current_y = word['top']
                        current_line.append(word)
                    elif abs(word['top'] - current_y) <= line_margin:
                        current_line.append(word)
                    else:
                        # 处理当前行
                        if current_line:
                            line_text = ' '.join(w['text'] for w in current_line)
                            text_blocks.append({
                                'text': line_text,
                                'page_number': page_num,
                                'bbox_x': min(w['x0'] for w in current_line),
                                'bbox_y': min(w['top'] for w in current_line),
                                'bbox_width': max(w['x1'] for w in current_line) - min(w['x0'] for w in current_line),
                                'bbox_height': max(w['bottom'] for w in current_line) - min(w['top'] for w in current_line)
                            })
                            text += line_text + "\n"
                        
                        # 开始新的一行
                        current_y = word['top']
                        current_line = [word]
                
                # 处理最后一行
                if current_line:
                    line_text = ' '.join(w['text'] for w in current_line)
                    text_blocks.append({
                        'text': line_text,
                        'page_number': page_num,
                        'bbox_x': min(w['x0'] for w in current_line),
                        'bbox_y': min(w['top'] for w in current_line),
                        'bbox_width': max(w['x1'] for w in current_line) - min(w['x0'] for w in current_line),
                        'bbox_height': max(w['bottom'] for w in current_line) - min(w['top'] for w in current_line)
                    })
                    text += line_text + "\n"
                
                text += "\n"  # 页面之间添加额外的换行
    except Exception as e:
        raise Exception(f"处理 PDF 文件时出错: {str(e)}")
    return text.strip(), text_blocks

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