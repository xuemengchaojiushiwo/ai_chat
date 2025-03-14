from typing import BinaryIO
import PyPDF2
from docx import Document

async def process_file(file: BinaryIO, mime_type: str) -> str:
    """处理不同类型的文件并提取文本"""
    if mime_type == 'text/plain':
        return file.read().decode('utf-8')
        
    elif mime_type == 'application/pdf':
        pdf_reader = PyPDF2.PdfReader(file)
        text = ''
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
        
    elif mime_type in ['application/msword', 
                      'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        doc = Document(file)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        
    elif mime_type == 'text/markdown':
        return file.read().decode('utf-8')
        
    raise ValueError(f'Unsupported file type: {mime_type}') 