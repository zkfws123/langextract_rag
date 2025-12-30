# Implementation Tasks: RAGFlow 企业级 RAG 系统

## 1. 文档解析模块 (Document Parser)
- [x] 1.1 创建 `src/parsers/` 目录结构
- [ ] 1.2 实现 `DocumentParser` 基类和接口
- [x] 1.3 实现 `MinerUParser` (集成现有 API 调用代码)
- [ ] 1.4 实现 `PDFParser` (本地 pymupdf 备选)
- [ ] 1.5 实现 `WordParser` (python-docx)
- [ ] 1.6 实现 `MarkdownParser`
- [ ] 1.7 实现 `HTMLParser`
- [ ] 1.8 添加解析器工厂模式
- [x] 1.9 添加解析进度追踪
- [ ] 1.10 编写解析器单元测试

## 2. 智能分块引擎 (Intelligent Chunking)
- [ ] 2.1 创建 `src/chunking/` 目录
- [ ] 2.2 实现 `ChunkStrategy` 接口
- [ ] 2.3 实现 `SemanticChunker` (基于语义相似度)
- [ ] 2.4 实现 `SlidingWindowChunker` (滑动窗口)
- [ ] 2.5 实现 `HierarchicalChunker` (层次化分块)
- [ ] 2.6 实现 `TableChunker` (表格特殊处理)
- [ ] 2.7 实现 `CodeChunker` (代码块处理)
- [ ] 2.8 添加分块质量评估指标
- [ ] 2.9 实现分块配置管理
- [ ] 2.10 编写分块器测试

## 3. 向量存储层 (Vector Store)
- [x] 3.1 创建 `src/retrieval/vector/` 目录
- [ ] 3.2 实现 `VectorStore` 抽象接口
- [x] 3.3 迁移 ChromaDB 实现 (从 notebook)
- [ ] 3.4 实现 FAISS 适配器
- [ ] 3.5 实现 Milvus 适配器 (可选)
- [x] 3.6 实现 Embeddings 管理 (复用阿里云百炼配置)
- [x] 3.7 添加批量索引功能
- [x] 3.8 添加向量库持久化
- [x] 3.9 实现相似度搜索接口
- [ ] 3.10 编写向量存储测试

## 4. 全文检索引擎 (Full-text Search)
- [ ] 4.1 创建 `src/retrieval/fulltext/` 目录
- [ ] 4.2 实现 BM25 检索器
- [ ] 4.3 实现 Elasticsearch 适配器 (可选)
- [ ] 4.4 添加分词和索引构建
- [ ] 4.5 实现关键词高亮
- [ ] 4.6 添加布尔查询支持
- [ ] 4.7 编写全文检索测试

## 5. 知识图谱层 (Knowledge Graph)
- [x] 5.1 创建 `src/graph/` 目录
- [x] 5.2 迁移 LangExtract 提取逻辑 (从 notebook)
- [x] 5.3 实现 `KnowledgeExtractor` 类
- [x] 5.4 定义 `Entity` 和 `Relation` 数据模型
- [ ] 5.5 实现 `GraphStore` 抽象接口
- [x] 5.6 实现 `InMemoryGraphStore` (基于 notebook 的内存字典)
- [x] 5.7 实现实体和关系存储（JSON 持久化）
- [x] 5.8 迁移 `graph_search` 函数实现多跳推理 (从 notebook)
- [x] 5.9 添加图谱溯源支持 (char_interval)
- [ ] 5.10 集成 networkx 用于图算法（社区发现、中心性计算）
- [ ] 5.11 实现 Neo4j 适配器 (可选升级)
- [ ] 5.12 编写知识图谱测试

## 6. 多路召回系统 (Hybrid Retrieval)
- [ ] 6.1 创建 `src/retrieval/hybrid/` 目录
- [ ] 6.2 实现 `HybridRetriever` 类
- [ ] 6.3 集成向量检索器
- [ ] 6.4 集成全文检索器
- [ ] 6.5 集成图谱检索器
- [ ] 6.6 实现 Reciprocal Rank Fusion (RRF) 重排序
- [ ] 6.7 实现 Cross-Encoder 重排序 (可选)
- [ ] 6.8 添加召回结果去重
- [ ] 6.9 添加召回评估指标 (MRR, NDCG)
- [ ] 6.10 编写混合检索测试

## 7. Agent 编排层 (Agent Orchestration)
- [x] 7.1 创建 `src/agents/` 目录
- [x] 7.2 迁移 LangGraph Agent 实现 (从 notebook)
- [x] 7.3 实现工具注册管理
- [x] 7.4 迁移 `vector_search_tool` (从 notebook)
- [x] 7.5 迁移 `graph_search_tool` (从 notebook)
- [x] 7.6 迁移 `hybrid_search_tool` (从 notebook)
- [ ] 7.7 实现 ReAct 推理流程
- [ ] 7.8 添加多步检索和验证
- [ ] 7.9 实现溯源链路 (char_interval → 原文)
- [ ] 7.10 添加对话历史管理
- [ ] 7.11 编写 Agent 集成测试

## 8. API 服务层 (FastAPI Service)
- [ ] 8.1 创建 `src/api/` 目录
- [ ] 8.2 初始化 FastAPI 应用
- [ ] 8.3 实现文档上传接口 (POST /documents)
- [ ] 8.4 实现文档解析接口 (POST /documents/parse)
- [ ] 8.5 实现查询接口 (POST /query)
- [ ] 8.6 实现流式查询接口 (POST /query/stream)
- [ ] 8.7 实现配置管理接口 (GET/PUT /config)
- [ ] 8.8 实现健康检查 (GET /health)
- [ ] 8.9 添加 API Key 认证中间件
- [ ] 8.10 添加请求日志和追踪
- [ ] 8.11 添加 Rate Limiting
- [ ] 8.12 实现 CORS 配置
- [ ] 8.13 添加 API 文档 (Swagger/OpenAPI)
- [ ] 8.14 编写 API 集成测试

## 9. 可视化界面 (Visualization UI)
- [ ] 9.1 创建 `src/ui/` 目录
- [ ] 9.2 初始化 Streamlit 应用
- [ ] 9.3 实现文档上传页面
- [ ] 9.4 实现文档解析预览
- [ ] 9.5 实现分块策略配置面板
- [ ] 9.6 实现召回结果对比视图
- [ ] 9.7 实现知识图谱可视化 (pyvis/networkx)
- [ ] 9.8 实现查询调试界面
- [ ] 9.9 实现溯源高亮显示
- [ ] 9.10 实现性能监控仪表盘
- [ ] 9.11 添加配置导入/导出
- [ ] 9.12 编写 UI 交互测试

## 10. 配置和环境管理
- [ ] 10.1 创建 `config/` 目录
- [ ] 10.2 设计配置文件结构 (YAML/TOML)
- [ ] 10.3 迁移 .env 配置
- [ ] 10.4 实现配置加载和验证
- [ ] 10.5 添加配置热重载
- [ ] 10.6 编写配置管理测试

## 11. 工具函数和通用模块
- [ ] 11.1 创建 `src/utils/` 目录
- [ ] 11.2 实现日志管理
- [ ] 11.3 实现错误处理
- [ ] 11.4 实现进度追踪
- [ ] 11.5 实现缓存管理
- [ ] 11.6 实现并发控制
- [ ] 11.7 编写工具函数测试

## 12. 数据库和持久化
- [ ] 12.1 设计数据库 Schema (文档元数据)
- [ ] 12.2 实现 SQLite/PostgreSQL 连接
- [ ] 12.3 实现文档元数据存储
- [ ] 12.4 实现查询历史记录
- [ ] 12.5 实现用户配置持久化
- [ ] 12.6 编写数据库迁移脚本

## 13. 测试和质量保证
- [ ] 13.1 配置 pytest 测试框架
- [ ] 13.2 编写单元测试套件
- [ ] 13.3 编写集成测试
- [ ] 13.4 实现端到端测试
- [ ] 13.5 添加测试覆盖率报告
- [ ] 13.6 实现性能基准测试
- [ ] 13.7 添加 CI/CD 配置 (GitHub Actions)

## 14. 文档和部署
- [ ] 14.1 创建 `docs/` 目录
- [ ] 14.2 编写架构设计文档
- [ ] 14.3 编写 API 使用文档
- [ ] 14.4 编写部署指南
- [ ] 14.5 编写用户手册
- [ ] 14.6 创建 Docker 镜像
- [ ] 14.7 编写 docker-compose 配置
- [ ] 14.8 创建 Kubernetes 部署配置 (可选)
- [ ] 14.9 编写性能调优指南

## 15. 优化和扩展
- [ ] 15.1 实现文档缓存机制
- [ ] 15.2 添加异步任务队列 (Celery/RQ)
- [ ] 15.3 实现分布式向量检索
- [ ] 15.4 添加模型热切换
- [ ] 15.5 实现增量更新图谱
- [ ] 15.6 添加多租户支持
- [ ] 15.7 实现查询优化器

## Dependencies to Install
```bash
# 核心依赖 (已有)
langextract
openai
python-dotenv
chromadb
langchain
langchain-openai
langchain-chroma

# 新增依赖
fastapi
uvicorn[standard]
streamlit
python-multipart
sqlalchemy
alembic
networkx  # 图算法（必需）
pyvis  # 图可视化
faiss-cpu  # or faiss-gpu
python-docx
pymupdf
beautifulsoup4
rank-bm25  # BM25 检索

# 可选依赖
neo4j  # 图数据库升级
elasticsearch  # 全文检索增强
redis  # 缓存
celery  # 异步任务队列
prometheus-client  # 监控
```

## Phase-by-Phase Completion

### Phase 1: Core Infrastructure (Weeks 1-2)
Tasks: 1.x, 2.x, 10.x, 11.x

### Phase 2: Retrieval System (Weeks 3-4)
Tasks: 3.x, 4.x, 5.x, 6.x

### Phase 3: Service Layer (Week 5)
Tasks: 8.x, 12.x

### Phase 4: Visualization & Agent (Week 6)
Tasks: 7.x, 9.x

### Phase 5: Testing & Optimization (Week 7)
Tasks: 13.x, 15.x

### Phase 6: Documentation & Deployment (Week 8)
Tasks: 14.x
