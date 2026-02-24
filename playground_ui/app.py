"""Streamlit playground - HTTP only, no backend imports."""

import streamlit as st

st.set_page_config(page_title="Retriever Playground", layout="wide")
st.title("Retriever Service Playground")
st.markdown("Upload documents and search. Communicates with backend via HTTP only.")

# --- 服务说明 ---
st.header("📖 服务说明")

st.markdown("""
本服务是一个 **Recall + Rerank** 检索服务（不包含生成），支持文档上传、多级分块、可插拔的 Embedding/Rerank 提供商、项目隔离、异步建索引和索引版本管理。

### 整体流程

1. **上传文档** → 将 PDF/PPTX/DOCX 上传到指定项目
2. **建索引** → 解析文档、分块、生成向量、写入向量库
3. **检索** → 对查询做 Embedding → 向量召回 (Recall) → 重排序 (Rerank) → 返回结果
4. **查看上下文** → 按需获取父级块及其子块，用于展开完整上下文
""")

st.subheader("API 调用方式")

st.markdown("""
所有接口基于 **HTTP**，Base URL 默认为 `http://localhost:8000/v1`。

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/v1/projects/{project_id}/files/upload` | 上传文件 |
| POST | `/v1/indexes/build` | 启动建索引任务 |
| GET | `/v1/jobs/{job_id}` | 查询任务状态 |
| POST | `/v1/projects/{project_id}/search` | Recall + Rerank 检索 |
| GET | `/v1/projects/{project_id}/parents/{parent_id}` | 获取父块及其子块 |
""")

st.subheader("1️⃣ 上传文件")

st.markdown("**请求**")
st.code("""
POST /v1/projects/{project_id}/files/upload
Content-Type: multipart/form-data

file: <binary>  # PDF / PPTX / DOCX
""", language="text")

st.markdown("**响应**")
st.code("""
{
  "file_id": "uuid-string",
  "filename": "example.pdf",
  "project_id": "default"
}
""", language="json")

st.subheader("2️⃣ 建索引")

st.markdown("**请求**")
st.code("""
POST /v1/indexes/build
Content-Type: application/json

{
  "project_id": "default",
  "file_ids": ["file-uuid-1", "file-uuid-2"],  // 可选，不传则建全量
  "index_version": null  // 可选，指定版本号
}
""", language="json")

st.markdown("**响应**")
st.code("""
{
  "job_id": "job-uuid"
}
""", language="json")

st.subheader("3️⃣ 查询任务状态")

st.markdown("**请求**")
st.code("GET /v1/jobs/{job_id}", language="text")

st.markdown("**响应**")
st.code("""
{
  "job_id": "job-uuid",
  "project_id": "default",
  "status": "pending | running | completed | failed",
  "index_version": "v1",
  "metrics": { "chunks_indexed": 100, ... },
  "error_message": null,
  "created_at": "2025-02-14T...",
  "updated_at": "2025-02-14T..."
}
""", language="json")

st.subheader("4️⃣ 检索 (Recall + Rerank)")

st.markdown("**请求**")
st.code("""
POST /v1/projects/{project_id}/search
Content-Type: application/json

{
  "query": "你的搜索问题",
  "index_version": null,      // 可选，不传用当前激活版本
  "recall_top_k": 50,         // 召回数量 1-200
  "rerank_top_n": 10,        // 重排后返回数量 1-100
  "filters": {},             // 可选过滤条件
  "debug": false             // 是否返回调试信息
}
""", language="json")

st.markdown("**响应**")
st.code("""
{
  "trace_id": "trace-uuid",
  "recall": [
    {
      "chunk_id": "chunk-uuid",
      "score": 0.85,
      "chunk_text": "文本片段...",
      "parent_id": "parent-uuid",
      "file_id": "file-uuid",
      "chunk_type": "text",
      "loc": { "page": 1, ... }
    }
  ],
  "rerank": [
    {
      "chunk_id": "chunk-uuid",
      "score": 0.92,
      "chunk_text": "文本片段...",
      "parent_id": "parent-uuid",
      "file_id": "file-uuid",
      "chunk_type": "text",
      "loc": { "page": 1, ... }
    }
  ],
  "timings_ms": { "embed": 10, "recall": 50, "rerank": 30 },
  "debug": {}
}
""", language="json")

st.subheader("5️⃣ 获取父块及子块")

st.markdown("**请求**")
st.code("GET /v1/projects/{project_id}/parents/{parent_id}", language="text")

st.markdown("**响应**")
st.code("""
{
  "parent_id": "parent-uuid",
  "parent_type": "page",
  "loc": { "page": 1 },
  "parent_text": "完整父级文本...",
  "children": [
    {
      "chunk_id": "chunk-uuid",
      "chunk_type": "text",
      "chunk_text": "子块文本...",
      "seq_start": 0,
      "seq_end": 100
    }
  ]
}
""", language="json")

st.markdown("---")
st.caption("左侧导航可进入 Upload 和 Search 页面进行实际操作。")
