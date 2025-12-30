# Proposal: RAGFlow 企业级 RAG 系统

## Why

基于现有的 Agentic-GraphRAG 教程 notebook，构建一个类似 RAGFlow 级别的企业级 RAG 系统。现有 notebook 提供了完整的技术原型，包含 MinerU PDF 解析、LangExtract 知识提取、ChromaDB 向量存储、知识图谱构建和 Agent 问答，但缺乏：
- 生产级的系统架构和模块化设计
- 智能分块策略和多路召回机制
- 可视化配置界面和调试工具
- RESTful API 服务层和企业级特性

本提案旨在将原型代码重构为完整的企业级 RAG 系统，实现文档解析、智能分块、多路召回（向量+全文+图谱）、可视化配置和 API 服务。

## What Changes

### 核心模块（基于现有 notebook）
1. **文档解析层** - 整合 MinerU API/本地部署，支持 PDF/Word/Markdown/HTML
2. **智能分块引擎** - 实现语义分块、滑动窗口、层次化分块、表格/代码特殊处理
3. **多路召回系统** - 向量检索(FAISS/Milvus) + 全文检索(BM25) + GraphRAG + 混合重排序
4. **知识图谱层** - 基于 LangExtract 的实体关系抽取、Neo4j 图谱存储、社区发现、多跳推理
5. **可视化界面** - Streamlit/Gradio 实现文档解析预览、分块策略配置、召回对比、图谱可视化
6. **API 服务层** - FastAPI 实现文档上传、查询接口、配置管理、日志追踪、权限控制
7. **Agent 编排** - LangGraph 实现工具注册、ReAct 推理、多步检索、结果验证

### 项目结构
```
src/
├── parsers/           # 文档解析器（MinerU 集成）
├── chunking/          # 智能分块引擎
├── retrieval/         # 多路召回系统
├── graph/             # 知识图谱（LangExtract + Neo4j）
├── agents/            # Agent 编排（LangGraph）
├── api/               # FastAPI 服务
├── ui/                # Streamlit 可视化界面
└── utils/             # 工具函数

config/                # 配置文件
tests/                 # 测试套件
docs/                  # 文档
```

### 技术栈（基于 notebook）
- **文档解析**: MinerU API/本地, python-docx, markdown
- **信息抽取**: LangExtract (已有完整实现)
- **向量存储**: ChromaDB (已有) / FAISS / Milvus
- **知识图谱**: InMemoryGraphStore (内存字典 + JSON，已有) / Neo4j (可选升级) / networkx (图算法)
- **全文检索**: Elasticsearch / BM25
- **LLM**: DeepSeek API (已配置)
- **Embeddings**: 阿里云百炼 text-embedding-v4 (已配置)
- **Agent 框架**: LangGraph 1.1 (已有示例)
- **API**: FastAPI
- **UI**: Streamlit/Gradio

## Impact

### 受影响的功能模块
- **新增**: document-parser, intelligent-chunking, hybrid-retrieval, knowledge-graph, visualization-ui, api-service, agent-orchestration
- **现有 notebook 代码**: 作为技术原型和参考实现，保留用于教学

### 迁移路径
1. 从 notebook 提取核心代码到模块化结构
2. 保留现有配置 (.env, API keys)
3. 逐步迁移功能到生产级实现
4. notebook 继续作为教程和快速原型验证

### 性能和扩展性
- 支持批量文档处理（并行化）
- 向量库可切换（ChromaDB → FAISS → Milvus）
- 分块策略可配置（通过 UI 实时调整）
- API 支持流式返回和异步处理

### 安全性
- API Key 管理和权限控制
- 文档上传大小限制和格式校验
- 查询频率限制（Rate Limiting）
- 日志审计和追踪

## Success Criteria

1. ✅ 文档解析成功率 > 95% (PDF/Word/Markdown)
2. ✅ 分块质量：语义完整性 > 90%
3. ✅ 检索召回率 > 85% (多路召回组合)
4. ✅ 知识图谱实体抽取 F1 > 0.8
5. ✅ API 响应时间 < 3s (P95)
6. ✅ UI 可用性：配置调整实时生效
7. ✅ Agent 溯源准确性 100% (char_interval 有效)

## Timeline Estimate

- **Phase 1** (Week 1-2): 文档解析和智能分块模块
- **Phase 2** (Week 3-4): 多路召回系统和知识图谱
- **Phase 3** (Week 5): API 服务层和权限管理
- **Phase 4** (Week 6): 可视化界面和 Agent 编排
- **Phase 5** (Week 7): 集成测试和性能优化
- **Phase 6** (Week 8): 文档和部署

## References

- Notebook: `Agentic-GraphRAG应用开发实战.ipynb` (完整技术原型)
- MinerU: https://github.com/opendatalab/MinerU
- LangExtract: 已实现完整提取流程
- RAGFlow: https://github.com/infiniflow/ragflow (参考架构)
- LightRAG: https://github.com/HKUDS/LightRAG (轻量化参考)
