# Implementation Tasks

## Phase 1: Backend - Knowledge Base Management

### 1.1 Data Models
- [ ] 创建 `src/knowledge_base/models.py`
  - `KnowledgeBase` 类（id, name, description, config_profile, created_at）
  - `KnowledgeBaseDocument` 类（kb_id, doc_hash, doc_name, status）
- [ ] 创建 `src/knowledge_base/store.py`
  - JSON持久化存储（`outputs/knowledge_bases/`）
  - CRUD操作

### 1.2 Knowledge Base Service
- [ ] 创建 `src/knowledge_base/service.py`
  - `create_knowledge_base(name, description, config_profile)`
  - `list_knowledge_bases()`
  - `get_knowledge_base(kb_id)`
  - `delete_knowledge_base(kb_id)`
  - `add_document_to_kb(kb_id, doc_hash, doc_name)`

### 1.3 增量知识积累
- [ ] 修改 `ChromaVectorStore` 支持按知识库分collection
  - collection命名: `kb_{kb_id}`
- [ ] 修改 `InMemoryGraphStore` 支持按知识库分图谱
  - 图谱存储: `outputs/knowledge_bases/{kb_id}/graph.json`
- [ ] 实现图谱增量合并逻辑

## Phase 2: UI Refactoring

### 2.1 侧边栏重构
- [ ] 知识库选择器组件
  - 下拉列表显示所有知识库
  - 新建知识库按钮
  - 删除知识库按钮
- [ ] 知识库详情展示
  - 包含文档数、实体数、关系数

### 2.2 文档上传流程
- [ ] 必须先选择知识库
- [ ] 上传后文档关联到当前知识库
- [ ] 增量提取：复用已有图谱

### 2.3 Agent聊天
- [ ] 知识库选择提示
- [ ] Agent工具绑定到当前知识库的vector/graph store

## Phase 3: Configuration

### 3.1 默认LLM配置
- [ ] 修改 `_resolve_llm_config()` 默认返回 sonetto5high
- [ ] 更新 `.env.example`

## Testing Checklist
- [ ] 创建新知识库
- [ ] 上传第一个文档
- [ ] 上传第二个文档（验证增量）
- [ ] 切换知识库
- [ ] Agent聊天使用正确知识库
