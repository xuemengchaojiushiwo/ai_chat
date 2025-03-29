import logging
import sys
from pathlib import Path

# 创建logs目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 配置日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 创建文件处理器
file_handler = logging.FileHandler(log_dir / "app.log", encoding='utf-8')
file_handler.setFormatter(formatter)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# 配置根日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# 创建专门的日志记录器
vector_logger = logging.getLogger("vector_store")
vector_logger.setLevel(logging.INFO)

chat_logger = logging.getLogger("chat")
chat_logger.setLevel(logging.INFO)

doc_logger = logging.getLogger("document")
doc_logger.setLevel(logging.INFO) 