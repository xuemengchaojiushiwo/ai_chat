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
      "id": 1,                    // 工作组唯一标识符
      "name": "研发团队",          // 工作组名称
      "description": "负责产品研发的团队", // 工作组描述
      "created_at": "2024-03-13T10:30:00Z" // 创建时间
    },
    {
      "id": 2,                    // 工作组唯一标识符
      "name": "市场团队",          // 工作组名称
      "description": "负责市场营销的团队", // 工作组描述
      "created_at": "2024-03-13T11:00:00Z" // 创建时间
    }
  ]
}
```

#### POST /api/workgroups
- 功能：创建新工作组
- 请求体示例：
```json
{
  "name": "产品团队",              // 工作组名称
  "description": "负责产品规划和设计的团队" // 工作组描述
}
```
- 返回示例：
```json
{
  "id": 3,                    // 工作组唯一标识符
  "name": "产品团队",          // 工作组名称
  "description": "负责产品规划和设计的团队", // 工作组描述
  "created_at": "2024-03-13T14:20:00Z" // 创建时间
}
```

#### PUT /api/workgroups/{id}
- 功能：更新工作组信息
- 请求体示例：
```json
{
  "name": "产品研发团队",        // 工作组名称
  "description": "负责产品规划、设计和开发的团队" // 工作组描述
}
```
- 返回示例：
```json
{
  "id": 3,                    // 工作组唯一标识符
  "name": "产品研发团队",      // 工作组名称
  "description": "负责产品规划、设计和开发的团队", // 工作组描述
  "created_at": "2024-03-13T14:20:00Z", // 创建时间
  "updated_at": "2024-03-13T15:30:00Z" // 更新时间
}
```

### 1.2 工作空间 (Workspace)

#### GET /api/workspaces
- 功能：获取工作空间列表
- 查询参数：
  - `group_id`: 工作组ID，用于筛选特定工作组下的工作空间
- 返回示例：
```json
{
  "workspaces": [
    {
      "id": 1,                    // 工作空间唯一标识符
      "name": "AI项目",           // 工作空间名称
      "description": "AI相关项目文档和对话", // 工作空间描述
      "group_id": 1,              // 所属工作组ID
      "created_at": "2024-03-13T10:35:00Z" // 创建时间
    },
    {
      "id": 2,                    // 工作空间唯一标识符
      "name": "市场调研",         // 工作空间名称
      "description": "市场调研资料和分析", // 工作空间描述
      "group_id": 1,              // 所属工作组ID
      "created_at": "2024-03-13T11:20:00Z" // 创建时间
    }
  ]
}
```

## 2. 文档管理 API

### 2.1 文档操作

#### GET /api/v1/documents/list
- 功能：获取文档列表
- 查询参数：
  - `show_all_versions`: 布尔值，是否显示所有版本（默认为 True，显示所有版本）
- 返回示例：
```json
{
  "documents": [
    {
      "id": 1,                    // 文档唯一标识符
      "dataset_id": 1,           // 数据集ID，用于文档分类管理
      "name": "产品需求文档.pdf",  // 文档名称
      "mime_type": "application/pdf", // 文档MIME类型
      "status": "processed",      // 文档处理状态
      "size": "1.2MB",           // 文档大小
      "version": 1,              // 文档版本号
      "file_hash": "abc123de",   // 文件哈希值，用于去重
      "created_at": "2024-03-13T10:40:00Z", // 创建时间
      "workspaces": [            // 关联的工作空间列表
        {
          "id": 1,               // 工作空间ID
          "name": "AI项目",       // 工作空间名称
          "description": "AI相关项目文档和对话" // 工作空间描述
        }
      ]
    }
  ]
}
```

#### POST /api/v1/documents/upload
- 功能：上传新文档
- 请求体示例（multipart/form-data）：
```
file: [二进制文件数据]
```
- 返回示例：
```json
{
  "id": 3,                    // 文档唯一标识符
  "dataset_id": 1,           // 数据集ID
  "name": "技术架构设计.pdf",  // 文档名称
  "mime_type": "application/pdf", // 文档MIME类型
  "status": "processing",     // 文档处理状态
  "size": "2.5MB",           // 文档大小
  "version": 1,              // 文档版本号
  "file_hash": "def456gh",   // 文件哈希值
  "created_at": "2024-03-13T14:30:00Z", // 创建时间
  "creator":"admin",//创建人
  "workspaces": []           // 关联的工作空间列表（初始为空）
}
```

### 2.2 文档工作空间关联

#### POST /api/v1/documents/link-workspaces
- 功能：关联多个文档到多个工作空间
- 请求体示例：
```json
{
  "document_ids": [1, 2, 3],  // 要关联的文档ID列表
  "workspace_ids": [1, 2]     // 要关联的工作空间ID列表
}
```
- 返回示例：
```json
{
  "status": "success",        // 操作状态
  "message": "Successfully linked 3 documents to 2 workspaces" // 操作结果描述
}
```

### 2.3 文档版本说明

文档系统支持版本控制，主要特点：
1. 每个文档都有唯一的文件哈希值和版本号
2. 相同文件（相同哈希值）会自动递增版本号
3. 默认显示所有版本，可通过 `show_all_versions` 参数控制显示
4. 文件名格式：`原始文件名_v版本号_哈希值前8位.扩展名`

### 2.4 支持的文件类型
```json
{
  "application/pdf": ".pdf",   // PDF文档
  "application/msword": ".doc", // Word文档（旧格式）
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx", // Word文档（新格式）
  "application/vnd.ms-excel": ".xls", // Excel文档（旧格式）
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx", // Excel文档（新格式）
  "text/plain": ".txt",        // 纯文本文件
  "text/csv": ".csv"          // CSV文件
}
```

### 2.5 文档状态说明
- `pending`: 等待处理（文档已上传但尚未开始处理）
- `processing`: 处理中（文档正在被系统处理）
- `processed`: 处理完成（文档处理成功，可以使用）
- `error`: 处理出错（文档处理失败）

### 2.6 文档下载

#### GET /api/v1/documents/download/{document_id}
- 功能：下载文档
- 返回：文件二进制流
- 响应头：
  ```
  Content-Disposition: attachment; filename="文件名"  // 下载时的文件名
  Content-Type: 文件MIME类型                        // 文件类型
  ```

### 2.7 文档状态查询

#### GET /api/v1/documents/status/{document_id}
- 功能：获取文档处理状态
- 返回示例：
```json
{
  "status": "processed",      // 文档处理状态
  "error": null,             // 错误信息（如果有）
  "created_at": "2024-03-13T14:30:00Z" // 创建时间
}
```

#### GET /api/v1/documents/embeddings/{document_id}
- 功能：检查文档的向量生成情况
- 返回示例：
```json
{
  "total_segments": 10,      // 文档总片段数
  "processed_segments": 10,  // 已处理的片段数
  "status": "completed"      // 处理状态
}
```

## 3. 对话管理 API

### 3.1 对话操作

#### GET /chat/conversations
- 功能：获取所有对话列表
- 返回示例：
```json
{
  "conversations": [
    {
      "id": 1,                    // 对话唯一标识符
      "name": "产品讨论",          // 对话名称
      "created_at": "2024-03-13T14:35:00Z", // 创建时间
      "messages": []              // 消息列表（初始为空）
    }
  ]
}
```

#### POST /chat/conversations
- 功能：创建新对话
- 请求体示例：
```json
{
  "name": "产品讨论",              // 对话名称
  "workspace_id": 1               // 所属工作空间ID
}
```
- 返回示例：
```json
{
  "id": 1,                    // 对话唯一标识符
  "name": "产品讨论",          // 对话名称
  "workspace_id": 1,          // 所属工作空间ID
  "created_at": "2024-03-13T14:35:00Z", // 创建时间
  "messages": []              // 消息列表（初始为空）
}
```

#### GET /chat/conversations/{conversation_id}/messages
- 功能：获取对话的消息历史
- 返回示例：
```json
{
  "messages": [
    {
      "id": 1,                    // 消息唯一标识符
      "conversation_id": 1,       // 所属对话ID
      "role": "user",             // 消息发送者角色（user/assistant）
      "content": "请分析一下产品需求文档中的核心功能", // 消息内容
      "tokens": 20,               // 消息的token数量
      "citations": [],            // 引用列表（初始为空）
      "created_at": "2024-03-13T14:36:00Z" // 创建时间
    },
    {
      "id": 2,                    // 消息唯一标识符
      "conversation_id": 1,       // 所属对话ID
      "role": "assistant",        // 消息发送者角色
      "content": "根据文档分析，核心功能包括...", // 消息内容
      "tokens": 150,              // 消息的token数量
      "citations": [              // 引用列表
        {
          "text": "系统应该支持多模态输入...", // 引用的原文内容
          "document_id": 1,       // 引用来源的文档ID
          "segment_id": 3,        // 文档中的片段ID
          "index": 1              // 引用在当前回复中的序号
        }
      ],
      "created_at": "2024-03-13T14:36:30Z" // 创建时间
    }
  ]
}
```

#### POST /chat/conversations/{conversation_id}/messages
- 功能：发送新消息并获取AI回复
- 请求体示例：
```json
{
  "message": "请分析一下产品需求文档中的核心功能", // 用户发送的消息内容
  "use_rag": true               // 是否启用文档知识库检索（RAG）功能
}
```
- 参数说明：
  - `message`: 用户发送的消息内容
  - `use_rag`: 是否启用文档知识库检索（RAG）功能
- 返回示例：
```json
{
  "id": 2,                    // 消息唯一标识符
  "conversation_id": 1,       // 所属对话ID
  "role": "assistant",        // 消息发送者角色
  "content": "根据文档分析，核心功能包括...", // 消息内容
  "tokens": 150,              // 消息的token数量
  "citations": [              // 引用列表
    {
      "text": "系统应该支持多模态输入...", // 引用的原文内容
      "document_id": 1,       // 引用来源的文档ID
      "segment_id": 3,        // 文档中的片段ID
      "index": 1              // 引用在当前回复中的序号
    }
  ],
  "created_at": "2024-03-13T14:36:30Z" // 创建时间
}
```

#### POST /chat/generate_title
- 功能：根据对话内容生成标题
- 请求体示例：
```json
{
  "message": "对话内容..."        // 用于生成标题的对话内容
}
```
- 返回示例：
```json
{
  "title": "生成的标题"           // AI生成的对话标题
}
```

### 3.2 引用说明

消息中的引用（citations）字段说明：
- `text`: 引用的原文内容（从文档中提取的相关文本）
- `document_id`: 引用来源的文档ID（用于定位源文档）
- `segment_id`: 文档中的片段ID（用于定位具体段落）
- `index`: 引用在当前回复中的序号（用于排序和展示）

## 4. 数据模型

### 4.1 Message（消息）
```json
{
  "id": 1,                    // 消息唯一标识符
  "conversation_id": 1,       // 所属对话ID
  "role": "user|assistant",   // 消息发送者角色
  "content": "消息内容",      // 消息正文
  "tokens": 20,               // 消息的token数量
  "citations": [              // 引用列表
    {
      "text": "引用的文本内容", // 引用的原文内容
      "document_id": 1,       // 引用来源的文档ID
      "segment_id": 1,        // 文档中的片段ID
      "index": 1              // 引用在当前回复中的序号
    }
  ],
  "created_at": "2024-03-13T14:36:00Z" // 创建时间
}
```

### 4.2 Citation（引用）
```json
{
  "text": "引用的文本内容",     // 引用的原文内容
  "document_id": 1,           // 引用来源的文档ID
  "segment_id": 1,            // 文档中的片段ID
  "index": 1                  // 引用在当前回复中的序号
}
```

## 5. 错误响应

### 5.1 参数错误 (400)
```json
{
  "error": "Bad Request",     // 错误类型
  "message": "参数错误说明",    // 错误描述
  "code": 400                 // HTTP状态码
}
```

### 5.2 未授权 (401)
```json
{
  "error": "Unauthorized",    // 错误类型
  "message": "请先登录",       // 错误描述
  "code": 401                 // HTTP状态码
}
```

### 5.3 禁止访问 (403)
```json
{
  "error": "Forbidden",       // 错误类型
  "message": "没有访问权限",    // 错误描述
  "code": 403                 // HTTP状态码
}
```

### 5.4 资源不存在 (404)
```json
{
  "error": "Not Found",       // 错误类型
  "message": "找不到指定的资源", // 错误描述
  "code": 404                 // HTTP状态码
}
```

### 5.5 服务器错误 (500)
```json
{
  "error": "Internal Server Error", // 错误类型
  "message": "服务器内部错误",      // 错误描述
  "code": 500                      // HTTP状态码
}
```

## 6. 注意事项

1. 所有请求需要在 Header 中包含认证信息：
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  // JWT认证令牌
```

2. RAG（检索增强生成）功能说明：
   - 通过设置 `use_rag: true` 启用文档知识库检索
   - 启用后，AI回复会基于相关文档内容生成答案
   - 引用信息会在 `citations` 字段中返回

3. 分页说明：
   - 列表接口默认返回最新的20条记录
   - 后续版本将添加分页参数支持

4. 错误处理：
   - 所有错误响应都包含 error、message 和 code 字段
   - 建议根据错误码进行相应的错误处理

5. 性能优化：
   - 建议在获取消息历史时使用分批加载
   - 对于长对话，可以只加载最近的消息

6. API版本控制：
   - 当前版本：v1
   - API路径默认不带版本号
   - 后续版本将通过路径前缀区分，如 /v2/chat/conversations

7. 创建对话必须指定工作空间ID，否则将返回400错误

8. 所有时间戳使用 ISO 8601 格式，UTC时区 