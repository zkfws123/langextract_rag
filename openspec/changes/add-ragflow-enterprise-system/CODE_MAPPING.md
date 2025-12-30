# Code Mapping: Notebook → Implementation

本文档标记每个实现任务对应的 notebook 代码位置，确保最大化复用已验证代码。

## 📄 Notebook 代码区域索引

### 区域1: 环境配置和依赖导入 (Lines 1-200)
- API Keys 配置 (DeepSeek, DashScope, MinerU)
- 核心库导入 (LangExtract, ChromaDB, LangChain)

### 区域2: MinerU PDF 解析 (Lines ~1500-1900)
- MinerU API 调用完整流程
- 上传URL请求 → PDF上传 → 轮询解析 → 下载结果
- Markdown 提取和保存

### 区域3: LangExtract 知识提取 (Lines ~1900-2700)
- Prompt 定义和 Few-shot 示例
- 多轮提取 (extraction_passes=3)
- 并行处理 (max_workers=20)
- char_interval 溯源机制

### 区域4: ChromaDB 向量存储 (Lines ~3100-4700)
- Embeddings 初始化 (阿里云百炼)
- 向量库创建和持久化
- KnowledgeExtraction 数据结构
- 批量索引和元数据保存

### 区域5: 知识图谱构建 (Lines ~4700-4900)
- 实体和关系提取
- 内存字典结构 knowledge_graph
- JSON 持久化
- entities 和 relations 数据模型

### 区域6: 图谱检索函数 (Lines ~4900-5000)
- graph_search(query_entity, hop=1) 核心函数
- 模糊匹配实体
- 多跳关系遍历
- 子图提取

### 区域7: LangChain Tools (Lines ~5000-5100)
- vector_search_tool 向量检索工具
- graph_search_tool 图谱检索工具
- hybrid_search_tool 混合检索工具
- 溯源信息整合

### 区域8: LangGraph Agent (Lines ~5100-5200)
- create_agent 创建 GraphRAG Agent
- 工具注册 [vector_search_tool, graph_search_tool, hybrid_search_tool]
- System Prompt 定义
- ReAct 推理流程

---

## 🔗 任务代码映射表

### 模块1: 文档解析器 (Document Parser)

| 任务 ID | 任务描述 | Notebook 代码位置 | 复用方式 |
|---------|---------|------------------|---------|
| 1.1 | 创建目录结构 | N/A | 新建 src/parsers/ |
| 1.2 | DocumentParser 基类 | N/A | 抽象接口 |
| 1.3 | MinerUParser | **Lines 1500-1900** | **直接迁移完整流程** |
| 1.4 | PDFParser (本地) | N/A | pymupdf 新实现 |
| 1.5 | WordParser | N/A | python-docx 新实现 |
| 1.6 | MarkdownParser | N/A | 简单封装 |
| 1.7 | HTMLParser | N/A | BeautifulSoup 新实现 |
| 1.8 | 解析器工厂 | N/A | 工厂模式包装 |
| 1.9 | 进度追踪 | **Lines 1700-1800 轮询逻辑** | **复用 MinerU 轮询代码** |
| 1.10 | 单元测试 | N/A | pytest 新建 |

**复用代码示例**:
```python
# src/parsers/mineru_parser.py
# 直接迁移 Lines 1560-1890
class MinerUParser(DocumentParser):
    def parse(self, pdf_path):
        # 步骤1: 请求上传URL (Line 1560-1580)
        # 步骤2: 上传PDF (Line 1600-1620)
        # 步骤3: 轮询解析 (Line 1640-1800)
        # 步骤4: 下载Markdown (Line 1820-1880)
```

---

### 模块2: 智能分块引擎 (Intelligent Chunking)

| 任务 ID | 任务描述 | Notebook 代码位置 | 复用方式 |
|---------|---------|------------------|---------|
| 2.1 | 创建目录 | N/A | 新建 src/chunking/ |
| 2.2 | ChunkStrategy 接口 | N/A | 抽象接口 |
| 2.3 | SemanticChunker | **隐含在 LangExtract** | 基于 max_char_buffer 参数 |
| 2.4 | SlidingWindowChunker | **LangExtract 内部实现** | 参考 chunk_size 机制 |
| 2.5 | HierarchicalChunker | N/A | 新实现（基于标题层级） |
| 2.6 | TableChunker | **MinerU 输出保留表格** | 检测表格标记 |
| 2.7 | CodeChunker | **MinerU 输出保留代码块** | 检测 ```代码``` |
| 2.8 | 质量评估 | N/A | 新实现 |
| 2.9 | 配置管理 | **Lines 1303-1320 配置示例** | **复用配置结构** |
| 2.10 | 单元测试 | N/A | pytest 新建 |

**复用代码示例**:
```python
# LangExtract 的分块参数 (Line 2660)
result = lx.extract(
    max_char_buffer=1000,  # ← 这是分块大小
    extraction_passes=3     # ← 多轮处理
)
# 迁移为 ChunkConfig
```

---

### 模块3: 向量存储层 (Vector Store)

| 任务 ID | 任务描述 | Notebook 代码位置 | 复用方式 |
|---------|---------|------------------|---------|
| 3.1 | 创建目录 | N/A | 新建 src/retrieval/vector/ |
| 3.2 | VectorStore 接口 | N/A | 抽象接口 |
| 3.3 | ChromaDB 实现 | **Lines 3160-4650** | **直接迁移完整代码** |
| 3.4 | FAISS 适配器 | N/A | 新实现（参考 ChromaDB） |
| 3.5 | Milvus 适配器 | N/A | 可选实现 |
| 3.6 | Embeddings 管理 | **Lines 4590-4600** | **复用阿里云百炼配置** |
| 3.7 | 批量索引 | **Lines 4650-4720** | **复用 vectorstore.add_texts()** |
| 3.8 | 持久化 | **Lines 3380-3390 CHROMA_PERSIST_DIR** | **复用持久化路径** |
| 3.9 | 相似度搜索 | **Lines 4800-4850 search_knowledge()** | **直接迁移** |
| 3.10 | 单元测试 | N/A | pytest 新建 |

**复用代码示例**:
```python
# src/retrieval/vector/chroma_store.py
# 直接迁移 Lines 4590-4720
class ChromaVectorStore(VectorStore):
    def __init__(self):
        # 复用 Line 4592-4606 的 Embeddings 初始化
        self.embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
            chunk_size=10  # 阿里云限制
        )
        # 复用 Line 4615-4620 的 Chroma 初始化
```

---

### 模块4: 全文检索引擎 (Full-text Search)

| 任务 ID | 任务描述 | Notebook 代码位置 | 复用方式 |
|---------|---------|------------------|---------|
| 4.1 | 创建目录 | N/A | 新建 src/retrieval/fulltext/ |
| 4.2 | BM25 检索器 | **隐含需求** | rank-bm25 库新实现 |
| 4.3 | Elasticsearch | N/A | 可选实现 |
| 4.4 | 分词索引 | **参考 LangExtract tokenization** | jieba 分词 |
| 4.5 | 关键词高亮 | N/A | 新实现 |
| 4.6 | 布尔查询 | N/A | 新实现 |
| 4.7 | 单元测试 | N/A | pytest 新建 |

**复用思路**: Notebook 中没有显式 BM25，但可参考向量检索的接口设计。

---

### 模块5: 知识图谱层 (Knowledge Graph)

| 任务 ID | 任务描述 | Notebook 代码位置 | 复用方式 |
|---------|---------|------------------|---------|
| 5.1 | 创建目录 | N/A | 新建 src/graph/ |
| 5.2 | LangExtract 提取 | **Lines 1950-2700** | **直接迁移完整逻辑** |
| 5.3 | KnowledgeExtractor | **Lines 2238-2676** | **封装为类** |
| 5.4 | Entity/Relation 模型 | **Lines 3200-3240 KnowledgeExtraction** | **直接复用 dataclass** |
| 5.5 | GraphStore 接口 | N/A | 抽象接口 |
| 5.6 | InMemoryGraphStore | **Lines 4746-4790** | **直接迁移字典结构** |
| 5.7 | JSON 持久化 | **Lines 4784-4790** | **直接复用 json.dump()** |
| 5.8 | graph_search 多跳 | **Lines 4900-4970** | **直接迁移函数** |
| 5.9 | char_interval 溯源 | **贯穿整个提取流程** | **保持不变** |
| 5.10 | networkx 集成 | **隐含需求** | 转换 knowledge_graph → nx.Graph |
| 5.11 | Neo4j 适配器 | N/A | 可选实现 |
| 5.12 | 单元测试 | N/A | pytest 新建 |

**复用代码示例**:
```python
# src/graph/in_memory_store.py
# 直接迁移 Lines 4746-4970
class InMemoryGraphStore(GraphStore):
    def __init__(self):
        # 复用 Line 4746-4750 的数据结构
        self.knowledge_graph = {
            "entities": {},
            "relations": []
        }
    
    def search(self, entity, hop=1):
        # 直接复用 Line 4900-4970 的 graph_search 函数
```

---

### 模块6: 多路召回系统 (Hybrid Retrieval)

| 任务 ID | 任务描述 | Notebook 代码位置 | 复用方式 |
|---------|---------|------------------|---------|
| 6.1 | 创建目录 | N/A | 新建 src/retrieval/hybrid/ |
| 6.2 | HybridRetriever | **Lines 5050-5075 hybrid_search_tool** | **直接迁移工具逻辑** |
| 6.3 | 集成向量检索 | **Lines 4800-4850 search_knowledge()** | **复用函数** |
| 6.4 | 集成全文检索 | N/A | 新增 BM25 |
| 6.5 | 集成图谱检索 | **Lines 4900-4970 graph_search()** | **复用函数** |
| 6.6 | RRF 重排序 | **隐含需求** | 新实现算法 |
| 6.7 | Cross-Encoder | N/A | 可选实现 |
| 6.8 | 结果去重 | **Line 5050-5075 隐含** | 新实现 |
| 6.9 | 评估指标 | N/A | 新实现 |
| 6.10 | 单元测试 | N/A | pytest 新建 |

**复用代码示例**:
```python
# src/retrieval/hybrid/hybrid_retriever.py
# 复用 Lines 5050-5075
class HybridRetriever:
    def search(self, query):
        # 复用 Line 5056 vector_result = vector_search_tool.invoke(query)
        # 复用 Line 5059-5066 graph_results 循环
        # 新增 BM25 检索
        # 新增 RRF 重排序
```

---

### 模块7: Agent 编排层 (Agent Orchestration)

| 任务 ID | 任务描述 | Notebook 代码位置 | 复用方式 |
|---------|---------|------------------|---------|
| 7.1 | 创建目录 | N/A | 新建 src/agents/ |
| 7.2 | LangGraph Agent | **Lines 5107-5150** | **直接迁移 create_agent** |
| 7.3 | 工具注册 | **Lines 4980-5076** | **直接复用 @tool 装饰器** |
| 7.4 | vector_search_tool | **Lines 4984-5008** | **直接迁移完整函数** |
| 7.5 | graph_search_tool | **Lines 5011-5040** | **直接迁移完整函数** |
| 7.6 | hybrid_search_tool | **Lines 5043-5075** | **直接迁移完整函数** |
| 7.7 | ReAct 推理 | **Lines 5125-5140 system_prompt** | **复用 Prompt** |
| 7.8 | 多步检索 | **Agent 内部机制** | 保持不变 |
| 7.9 | 溯源链路 | **Lines 4999-5006 char_interval 展示** | **复用格式化逻辑** |
| 7.10 | 对话历史 | **隐含需求** | 新增 session 管理 |
| 7.11 | 集成测试 | N/A | pytest 新建 |

**复用代码示例**:
```python
# src/agents/graphrag_agent.py
# 直接迁移 Lines 4980-5150
from langchain.tools import tool
from langchain.agents import create_agent

# 复用 Line 4984-5008
@tool
def vector_search_tool(query: str) -> str:
    # 完全一样的代码

# 复用 Line 5122-5140
graphrag_agent = create_agent(
    model=llm,
    tools=[vector_search_tool, graph_search_tool, hybrid_search_tool],
    system_prompt="""..."""  # 复用完整 Prompt
)
```

---

### 模块8: API 服务层 (FastAPI Service)

| 任务 ID | 任务描述 | Notebook 代码位置 | 复用方式 |
|---------|---------|------------------|---------|
| 8.1 | 创建目录 | N/A | 新建 src/api/ |
| 8.2 | FastAPI 初始化 | N/A | 新建 main.py |
| 8.3 | 文档上传接口 | **MinerU 上传逻辑** | 封装为 /documents 端点 |
| 8.4 | 文档解析接口 | **MinerU 完整流程** | 封装为 /documents/parse |
| 8.5 | 查询接口 | **Agent invoke** | 封装为 POST /query |
| 8.6 | 流式查询 | **Agent stream** | 封装为 /query/stream |
| 8.7 | 配置管理 | **Lines 1303-1390 配置加载** | **复用 .env 逻辑** |
| 8.8 | 健康检查 | N/A | 新建 /health |
| 8.9 | API Key 认证 | N/A | 新实现 middleware |
| 8.10 | 请求日志 | N/A | 新实现 logging |
| 8.11 | Rate Limiting | N/A | 新实现 |
| 8.12 | CORS | N/A | 新实现 |
| 8.13 | API 文档 | N/A | FastAPI 自动生成 |
| 8.14 | 集成测试 | N/A | pytest + httpx |

**复用代码示例**:
```python
# src/api/main.py
from fastapi import FastAPI
app = FastAPI()

@app.post("/query")
async def query(question: str):
    # 复用 Agent 调用逻辑
    result = graphrag_agent.invoke(question)
    return {"answer": result}
```

---

### 模块9: 可视化界面 (Visualization UI)

| 任务 ID | 任务描述 | Notebook 代码位置 | 复用方式 |
|---------|---------|------------------|---------|
| 9.1 | 创建目录 | N/A | 新建 src/ui/ |
| 9.2 | Streamlit 初始化 | N/A | 新建 app.py |
| 9.3 | 文档上传页面 | N/A | st.file_uploader |
| 9.4 | 解析预览 | **MinerU Markdown 输出** | 显示 markdown_text |
| 9.5 | 分块配置面板 | **Lines 2660-2670 参数** | 映射为 UI 控件 |
| 9.6 | 召回结果对比 | **Lines 5050-5075 混合检索** | 并排展示 |
| 9.7 | 图谱可视化 | **knowledge_graph 结构** | pyvis 渲染 |
| 9.8 | 查询调试 | **Agent 执行过程** | 展示工具调用链 |
| 9.9 | 溯源高亮 | **char_interval** | 高亮原文片段 |
| 9.10 | 性能监控 | N/A | 新实现 metrics |
| 9.11 | 配置导入导出 | **配置结构** | JSON 序列化 |
| 9.12 | 交互测试 | N/A | 手动测试 |

**复用代码示例**:
```python
# src/ui/app.py
import streamlit as st

# 复用 knowledge_graph 结构
if st.button("可视化图谱"):
    # 加载 knowledge_graph.json
    # 使用 pyvis 渲染
```

---

## 📊 复用统计

| 模块 | 总任务数 | 直接复用 | 改造复用 | 新实现 |
|-----|---------|---------|---------|--------|
| 文档解析 | 10 | 2 (20%) | 1 (10%) | 7 (70%) |
| 智能分块 | 10 | 0 | 3 (30%) | 7 (70%) |
| 向量存储 | 10 | 5 (50%) | 3 (30%) | 2 (20%) |
| 全文检索 | 7 | 0 | 1 (14%) | 6 (86%) |
| 知识图谱 | 12 | 6 (50%) | 2 (17%) | 4 (33%) |
| 多路召回 | 10 | 3 (30%) | 2 (20%) | 5 (50%) |
| Agent编排 | 11 | 7 (64%) | 1 (9%) | 3 (27%) |
| API服务 | 14 | 0 | 5 (36%) | 9 (64%) |
| 可视化 | 12 | 0 | 4 (33%) | 8 (67%) |
| **总计** | **96** | **23 (24%)** | **22 (23%)** | **51 (53%)** |

## ✅ 核心复用点

### 高复用模块 (>50% 直接复用)
1. ✅ **Agent编排** (64%) - ✓ 已完成 `src/agents/` (agent.py, tools.py)
2. ✅ **知识图谱** (50%) - ✓ 已完成 `src/graph/` (in_memory_store.py, models.py)
3. ✅ **向量存储** (50%) - ✓ 已完成 `src/retrieval/vector/chroma_store.py`

### 中度复用模块 (30-50%)
4. ⚠️ **多路召回** (30% 直接 + 20% 改造)
5. ⚠️ **智能分块** (30% 改造)
6. ⚠️ **API服务** (36% 改造)

### 低复用模块 (<30%)
7. ❌ **全文检索** (14%) - 需要新实现 BM25
8. ❌ **文档解析** (20%) - 仅 MinerU 可复用
9. ❌ **可视化** (33% 改造) - UI 层需要新建

## 🎯 实施优先级（基于复用率）

### Phase 1: 高复用模块优先 (Week 1-2)
1. 向量存储层 (50% 复用) → 快速搭建
2. 知识图谱层 (50% 复用) → 快速搭建
3. 文档解析层 (MinerU 20% 复用) → 快速集成

### Phase 2: Agent 和检索 (Week 3-4)
4. Agent编排 (64% 复用) → 直接迁移
5. 多路召回 (30%+20% 复用) → 整合检索器
6. 全文检索 (14% 复用) → 新增 BM25

### Phase 3-6: 保持原计划
继续 API、UI、测试、部署

---

## 🔍 代码迁移清单

### 必须迁移的核心代码（优先级P0）
- [x] Lines 1500-1900: MinerU PDF 解析完整流程 → `src/parsers/mineru_parser.py`
- [x] Lines 1950-2700: LangExtract 知识提取和溯源 → `src/parsers/knowledge_extractor.py`
- [x] Lines 3200-3240: KnowledgeExtraction 数据结构 → `src/graph/models.py`
- [x] Lines 4590-4720: ChromaDB 向量存储初始化和索引 → `src/retrieval/vector/chroma_store.py`
- [x] Lines 4746-4790: 知识图谱内存结构和JSON持久化 → `src/graph/in_memory_store.py`
- [x] Lines 4800-4850: search_knowledge 向量检索函数 → `src/parsers/knowledge_extractor.py`
- [x] Lines 4900-4970: graph_search 多跳图谱检索 → `src/graph/in_memory_store.py`
- [x] Lines 4984-5075: 三个 LangChain Tools (vector/graph/hybrid) → `src/agents/tools.py`
- [x] Lines 5107-5150: LangGraph Agent 创建和 Prompt → `src/agents/agent.py`

### 可改造复用的代码（优先级P1）
- [ ] Lines 2660-2670: LangExtract 分块参数 → ChunkConfig
- [x] Lines 1303-1390: 环境配置加载 → 配置管理模块 (`.env`)
- [x] Lines 5050-5075: hybrid_search_tool 逻辑 → `src/agents/tools.py`

### 需要新实现的模块（优先级P2）
- [ ] BM25 全文检索器
- [ ] RRF 重排序算法
- [ ] FastAPI 接口封装
- [ ] Streamlit UI 界面

---

## 📝 迁移注意事项

1. **保持接口兼容**: 迁移时保持函数签名不变，确保单元测试可以直接运行
2. **保留注释**: Notebook 中的注释和说明要完整迁移到代码中
3. **环境变量**: 确保 .env 配置在模块化后依然有效
4. **错误处理**: Notebook 中部分代码缺少异常处理，迁移时需要补充
5. **日志记录**: 将 print() 语句替换为 logging 模块
6. **类型提示**: 添加 Python type hints 提高代码可维护性

---

## 🚀 快速开始

```bash
# 1. 创建项目结构 ✓ 已完成
mkdir -p src/{parsers,chunking,retrieval/{vector,fulltext,hybrid},graph,agents,api,ui,utils}

# 2. 核心代码已迁移 ✓ 已完成
# - src/parsers/mineru_parser.py (MinerU PDF解析)
# - src/parsers/knowledge_extractor.py (LangExtract知识提取)
# - src/graph/in_memory_store.py (知识图谱存储)
# - src/graph/models.py (数据模型)
# - src/retrieval/vector/chroma_store.py (向量存储)
# - src/agents/tools.py (检索工具)
# - src/agents/agent.py (LangGraph Agent)

# 3. 安装依赖 ✓ 已完成
pip install langextract openai chromadb langchain-openai langchain-chroma langgraph

# 4. 配置环境变量 ✓ 已完成
# .env 文件包含 DEEPSEEK_API_KEY, DASHSCOPE_API_KEY, MINERU_API_KEY

# 5. 运行端到端测试 ✓ 已验证
python -c "
from src.agents import build_agent, agent_query
from src.parsers.knowledge_extractor import KnowledgeExtractor
# ... 完整流程已通过测试
"
```
