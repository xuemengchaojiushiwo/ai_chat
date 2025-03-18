# AI Chat Backend

AI Chat 是一个基于 FastAPI 的智能对话系统后端，支持文档知识库检索增强的对话功能。

## 功能特点

- 基于大语言模型的智能对话
- 支持 RAG (检索增强生成) 功能
- 文档知识库管理
- 工作组和工作空间管理
- RESTful API 接口

## 技术栈

- Python 3.8+
- FastAPI
- SQLAlchemy (异步)
- Alembic (数据库迁移)
- Pydantic
- Silicon Flow API / OpenAI API

## 系统要求

- Python 3.10
- pip (Python 包管理器)
- 虚拟环境工具 (推荐使用 venv 或 conda)

## 安装步骤

1. 克隆项目并进入项目目录：
```bash
git clone [项目地址]
cd ai_chat
```

2. 创建并激活虚拟环境：
```bash
# 使用 venv
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```




## 启动服务

1. 开发模式启动：
```bash
uvicorn ai_chat.api.main:app --reload
```
服务将在 http://localhost:8000 启动，支持代码热重载。


## API 文档

启动服务后，可以通过以下地址访问 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

详细的 API 文档请参考 `docs/api_documentation.md`。

## 项目结构

```
ai_chat/
├── alembic/            # 数据库迁移配置
├── api/                # API 接口
│   ├── main.py        # 主应用
│   ├── schemas.py     # 数据模型
│   └── ...
├── chat/              # 对话相关功能
├── knowledge/         # 知识库管理
├── models/           # 数据库模型
├── utils/            # 工具函数
├── docs/             # 文档
├── tests/            # 测试用例
├── config.py         # 配置文件
├── database.py       # 数据库配置
└── run.py            # 应用入口
```

## 开发指南

1. 代码风格
- 遵循 PEP 8 规范
- 使用 Black 进行代码格式化
- 使用 isort 进行导入排序

2. 测试
```bash
# 运行测试
pytest

# 带覆盖率的测试
pytest --cov=ai_chat
```

3. 数据库迁移
```bash
# 创建新的迁移
alembic revision --autogenerate -m "描述变更内容"

# 更新数据库
alembic upgrade head

# 回滚到上一个版本
alembic downgrade -1
```

## 常见问题

1. 数据库连接错误
- 检查 DATABASE_URL 配置是否正确
- 确保数据库文件有正确的访问权限

2. API 密钥配置
- 确保已正确设置 SF_API_KEY 或 OPENAI_API_KEY
- 检查 API 基础URL配置是否正确

3. 启动错误
- 检查所有依赖是否正确安装
- 确保数据库迁移已执行
- 查看日志文件获取详细错误信息

## 许可证

[添加许可证信息]

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交变更
4. 推送到分支
5. 创建 Pull Request

## 联系方式

[添加联系方式] 