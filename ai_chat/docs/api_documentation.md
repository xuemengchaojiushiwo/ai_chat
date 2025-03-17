# AI Chat API 文档

## 1. 工作空间管理 API

### 1.1 工作组 (Workgroup)

#### GET /api/workgroups
- 功能：获取所有工作组列表
- 返回示例：
```json
{
  "workgroups": [
    {
      "id": 1,
      "name": "研发团队",
      "description": "负责产品研发的团队",
      "created_at": "2024-03-13T10:30:00Z"
    },
    {
      "id": 2,
      "name": "市场团队",
      "description": "负责市场营销的团队",
      "created_at": "2024-03-13T11:00:00Z"
    }
  ]
}
```

#### POST /api/workgroups
- 功能：创建新工作组
- 请求体示例：
```json
{
  "name": "产品团队",
  "description": "负责产品规划和设计的团队"
}
```
- 返回示例：
```json
{
  "id": 3,
  "name": "产品团队",
  "description": "负责产品规划和设计的团队",
  "created_at": "2024-03-13T14:20:00Z"
}
```

#### PUT /api/workgroups/{id}
- 功能：更新工作组信息
- 请求体示例：
```json
{
  "name": "产品研发团队",
  "description": "负责产品规划、设计和开发的团队"
}
```
- 返回示例：
```json
{
  "id": 3,
  "name": "产品研发团队",
  "description": "负责产品规划、设计和开发的团队",
  "created_at": "2024-03-13T14:20:00Z",
  "updated_at": "2024-03-13T15:30:00Z"
}
```

### 1.2 工作空间 (Workspace)

#### GET /api/workspaces
- 功能：获取工作空间列表
- 查询参数示例：`?group_id=1`
- 返回示例：
```json
{
  "workspaces": [
    {
      "id": 1,
      "name": "AI项目",
      "description": "AI相关项目文档和对话",
      "group_id": 1,
      "created_at": "2024-03-13T10:35:00Z"
    },
    {
      "id": 2,
      "name": "市场调研",
      "description": "市场调研资料和分析",
      "group_id": 1,
      "created_at": "2024-03-13T11:20:00Z"
    }
  ]
}
```

## 2. 文档管理 API

### 2.1 文档操作

#### GET /api/documents
- 功能：获取文档列表
- 返回示例：
```json
{
  "documents": [
    {
      "id": 1,
      "name": "产品需求文档.pdf",
      "mime_type": "application/pdf",
      "status": "processed",
      "created_at": "2024-03-13T10:40:00Z"
    },
    {
      "id": 2,
      "name": "市场分析报告.docx",
      "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "status": "processing",
      "created_at": "2024-03-13T11:25:00Z"
    }
  ]
}
```

#### POST /api/documents
- 功能：上传新文档
- 请求体示例（multipart/form-data）：
```
file: [二进制文件数据]
```
- 返回示例：
```json
{
  "id": 3,
  "name": "技术架构设计.pdf",
  "mime_type": "application/pdf",
  "status": "processing",
  "created_at": "2024-03-13T14:30:00Z"
}
```

### 2.2 文档工作空间关联

#### POST /api/documents/{document_id}/workspaces
- 功能：关联文档到工作空间
- 请求体示例：
```json
{
  "workspace_ids": [1, 2]
}
```
- 返回示例：
```json
{
  "success": true,
  "message": "文档已成功关联到指定工作空间"
}
```

## 3. 对话管理 API

### 3.1 对话操作

#### POST /chat/conversations
- 功能：创建新对话
- 请求体示例：
```json
{
  "name": "产品讨论",
  "workspace_id": 1
}
```
- 返回示例：
```json
{
  "id": 1,
  "name": "产品讨论",
  "workspace_id": 1,
  "created_at": "2024-03-13T14:35:00Z",
  "messages": []
}
```

#### POST /chat/conversations/{conversation_id}/messages
- 功能：发送新消息
- 请求体示例：
```json
{
  "message": "请分析一下产品需求文档中的核心功能",
  "use_rag": true
}
```
- 返回示例：
```json
{
  "id": 1,
  "conversation_id": 1,
  "content": "根据产品需求文档分析，核心功能包括：\n1. 文档智能处理\n2. 多轮对话支持\n3. 知识库检索...",
  "role": "assistant",
  "created_at": "2024-03-13T14:36:00Z"
}
```

## 4. 数据模型示例

### 4.1 User（用户）
```json
{
  "id": 1,
  "email": "user@example.com",
  "name": "张三",
  "status": "active",
  "last_login_at": "2024-03-13T10:00:00Z",
  "created_at": "2024-03-01T09:00:00Z",
  "updated_at": "2024-03-13T10:00:00Z"
}
```

### 4.2 Workspace（工作空间）
```json
{
  "id": 1,
  "name": "AI项目空间",
  "description": "用于AI项目开发和文档管理",
  "created_at": "2024-03-01T09:30:00Z"
}
```

### 4.3 Document（文档）
```json
{
  "id": 1,
  "name": "AI系统设计文档.pdf",
  "content": "文档内容...",
  "mime_type": "application/pdf",
  "status": "processed",
  "created_at": "2024-03-13T11:00:00Z"
}
```

### 4.4 Conversation（对话）
```json
{
  "id": 1,
  "title": "AI系统设计讨论",
  "workspace_id": 1,
  "created_at": "2024-03-13T14:00:00Z",
  "messages": [
    {
      "id": 1,
      "content": "请解释一下系统架构图",
      "role": "user",
      "created_at": "2024-03-13T14:01:00Z"
    },
    {
      "id": 2,
      "content": "系统架构主要分为以下几层...",
      "role": "assistant",
      "created_at": "2024-03-13T14:01:30Z"
    }
  ]
}
```

## 5. 错误响应示例

### 5.1 参数错误 (400)
```json
{
  "error": "Bad Request",
  "message": "workspace_id 是必需的参数",
  "code": 400
}
```

### 5.2 未授权 (401)
```json
{
  "error": "Unauthorized",
  "message": "请先登录",
  "code": 401
}
```

### 5.3 禁止访问 (403)
```json
{
  "error": "Forbidden",
  "message": "没有访问权限",
  "code": 403
}
```

### 5.4 资源不存在 (404)
```json
{
  "error": "Not Found",
  "message": "找不到指定的文档",
  "code": 404
}
```

## 6. 注意事项

1. 所有请求需要在 Header 中包含认证信息：
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

2. 文件上传限制：
   - 最大文件大小：30MB
   - 支持的文件类型：txt, pdf, doc, docx, md

3. API 基础路径：`http://localhost:8000`

4. 创建对话必须指定工作空间ID，否则将返回400错误

5. 所有时间戳使用 ISO 8601 格式，UTC时区 