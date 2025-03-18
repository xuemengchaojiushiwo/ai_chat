import os
import magic
from docx import Document as DocxDocument  # 重命名以避免冲突
from PyPDF2 import PdfReader
import markdown
from typing import Optional, Tuple, List

def process_file(file_path: str) -> Tuple[str, str]:
    """
    处理不同类型的文件并提取文本内容
    返回: (文本内容, MIME类型)
    """
    mime = magic.Magic(mime=True)
    mime_type = mime.from_file(file_path)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    try:
        if mime_type == 'application/pdf':
            return process_pdf(file_path), mime_type
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return process_docx(file_path), mime_type
        elif mime_type == 'text/markdown' or file_path.endswith('.md'):
            return process_markdown(file_path), 'text/markdown'
        elif mime_type.startswith('text/'):
            return process_text(file_path), mime_type
        else:
            raise ValueError(f"不支持的文件类型: {mime_type}")
    except Exception as e:
        raise Exception(f"处理文件时出错: {str(e)}")

def process_pdf(file_path: str) -> str:
    """处理 PDF 文件"""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf = PdfReader(file)
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        raise Exception(f"处理 PDF 文件时出错: {str(e)}")
    return text.strip()

def process_docx(file_path: str) -> str:
    """处理 Word 文档"""
    text = ""
    try:
        doc = DocxDocument(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        raise Exception(f"处理 Word 文档时出错: {str(e)}")
    return text.strip()

def process_markdown(file_path: str) -> str:
    """处理 Markdown 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            # 转换 Markdown 为纯文本
            html = markdown.markdown(text)
            # TODO: 可以添加 HTML 到纯文本的转换
            return text
    except Exception as e:
        raise Exception(f"处理 Markdown 文件时出错: {str(e)}")

def process_text(file_path: str) -> str:
    """处理纯文本文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except Exception as e:
        raise Exception(f"处理文本文件时出错: {str(e)}") 