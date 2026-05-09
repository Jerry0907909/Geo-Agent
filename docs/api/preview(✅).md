# API 接口概览

地质文献智能体提供了一套 RESTful API，用于文献检索、Agent 问答和文档管理。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **版本**: `v1.0.0`
- **Content-Type**: `application/json`

## 核心端点

| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `POST` | `/api/rag/query` | **RAG 检索** - 执行向量检索并生成答案 |
| `POST` | `/api/agent/query` | **Agent 智能查询** - 执行复杂的多步推理任务 |
| `POST` | `/api/documents/upload` | **上传文献** - 上传并索引新文献 |
| `GET` | `/api/documents/list` | **文献列表** - 获取已索引的文献 |
| `GET` | `/api/health` | **健康检查** - 检查服务运行状态 |

## 调用示例

### RAG 检索

```bash
curl -X POST "http://localhost:8000/api/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "华北克拉通的地质特征",
    "top_k": 5
  }'
```

### Agent 查询

```bash
curl -X POST "http://localhost:8000/api/agent/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "对比华北克拉通和扬子克拉通",
    "max_iterations": 10,
    "return_intermediate_steps": true
  }'
```

## 错误码

| 代码 | 描述 |
| :--- | :--- |
| `200` | 成功 |
| `422` | 参数验证失败 |
| `500` | 服务器内部错误 |
