# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **GraphRAG (Graph-based Retrieval Augmented Generation)** knowledge base system that combines:
- **LangExtract** for structured knowledge extraction from documents
- **ChromaDB** for vector-based semantic search
- **Knowledge Graph** for entity-relationship storage and traversal
- **LangGraph Agent** for intelligent Q&A with evidence tracing
- **Streamlit UI** for interactive document processing and querying

The system extracts structured knowledge from PDFs (using MinerU OCR), builds both vector and graph indexes, and provides hybrid retrieval for accurate question answering.

## Core Architecture

### 1. Knowledge Extraction Pipeline (`src/parsers/`)

**Two-stage extraction process:**

- **Stage 1: Entity Extraction** (`knowledge_extractor.py`)
  - Uses LangExtract with LLM to extract structured entities from text
  - Supports custom prompts and domain-specific extraction (e.g., ZiWei DouShu)
  - Handles long documents via automatic chunking with char_interval tracking
  - Parallel chunk processing via `EXTRACTION_PARALLEL_WORKERS` env var
  - Robust error handling with multiple retry strategies (force_json, fence_output)

- **Stage 2: Relation Extraction** (`relation_extractor.py`)
  - Analyzes extracted entities to identify relationships
  - Builds relation triples (subject, relation, object) with confidence scores
  - Optional stage controlled by `enable_relation_extraction` flag

- **Pipeline Orchestration** (`pipeline.py`)
  - `KnowledgeExtractionPipeline` coordinates both stages
  - Configurable via `EXTRACTION_QUIET` env var for logging control

### 2. Document Parsing (`src/parsers/`)

- **MinerU Parser** (`mineru_parser.py`)
  - Cloud-based PDF OCR service with VPN/proxy handling
  - Returns per-page markdown with char offsets for precise traceability
  - Converts HTML tables to markdown format
  - Handles CDN download issues with curl fallback and DoH DNS resolution

- **Local PDF Parser** (`local_pdf_parser.py`)
  - Fallback for local PDF processing

### 3. Storage Layer

**Knowledge Base Service** (`src/knowledge_base/kb_service.py`)
- Manages knowledge bases (CRUD operations)
- File-based storage in `outputs/knowledge_bases/{kb_id}/`
- Each KB contains: config.json, graph.json, documents/{doc_id}/
- Document artifacts: content.md, pages.json, extractions.json, meta.json

**Vector Store** (`src/retrieval/vector/chroma_store.py`)
- ChromaDB with DashScope embeddings (text-embedding-v4)
- Per-KB collections named `kb_{kb_id}`
- Indexes extraction searchable text with metadata

**Graph Store** (`src/graph/in_memory_store.py`)
- In-memory knowledge graph: `{"entities": {}, "relations": []}`
- Entities have type, attributes, mentions (with source + char_interval)
- Relations have subject, object, relation, source, confidence
- Supports multi-hop graph traversal search

### 4. Agent System (`src/agents/`)

**GraphRAG Agent** (`agent.py`)
- LangChain agent with three tools: vector_search, graph_search, hybrid_search
- **Enforced evidence tracing**: Agent MUST call tools before answering
- Returns structured response: {question, answer, evidence}
- Supports multiple LLM backends via `ACTIVE_LLM` env var:
  - `ds`: DeepSeek
  - `gemini3flash`, `gemini3pro`: Google Gemini
  - `sonetto5high`, `sonetto_gemini3pro`: Sonetto gateway

**Tools** (`tools.py`)
- `vector_search_tool`: Semantic similarity search in ChromaDB
- `graph_search_tool`: Entity-centric graph traversal
- `hybrid_search_tool`: Combines vector + graph results (recommended)

### 5. UI Layer (`src/ui/`)

**Streamlit App** (`app.py`)
- Modular tab-based interface with iOS-inspired dark theme
- Session management via `session.py` (singleton pattern)
- UI logging system captures extraction/indexing progress

**Tabs:**
- `chat_tab.py`: Q&A interface with agent evidence display
- `ocr_tab.py`: MinerU vs local OCR comparison
- `preview_tab.py`: Document markdown preview with page navigation
- `graph_tab.py`: Interactive knowledge graph visualization
- `extractions_tab.py`: View/edit extracted entities
- `insights_tab.py`: Statistics and analytics

**Sidebars:**
- `kb_sidebar.py`: Knowledge base selection and management
- `settings_sidebar.py`: LLM/extraction config (model selection, custom prompts)
- `doc_workflow.py`: Document upload and processing workflow

## Development Commands

### Running the Application

```bash
# Start Streamlit UI
streamlit run src/ui/app.py

# Quick smoke test (import checks)
python quick_test.py
```

### Testing

```bash
# Test extraction pipeline
python test_simple_extract.py

# Test agent with logging
python test_agent_logging.py

# Test API connection
python test_api_connection.py

# Test chunked extraction
python test_chunked_extraction.py

# Test OCR document extraction
python test_ocr_doc_extraction.py

# Debug graph search
python debug_graph_search.py

# Debug extraction classes
python debug_ziwei_extraction_class.py
```

### Environment Configuration

Required `.env` file (see `.env.example`):

```bash
# LLM for extraction/agent
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEFAULT_MODEL=deepseek-chat

# Optional: Gemini/Sonetto
GEMINI_API_KEY=your_key
GEMINI_BASE_URL=...
SONETTO_API_KEY=your_key
SONETTO_BASE_URL=...

# Embeddings (DashScope/Aliyun)
DASHSCOPE_API_KEY=your_key
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4

# MinerU OCR
MINERU_API_KEY=your_key
MINERU_BASE_URL=https://mineru.net

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_db
COLLECTION_NAME=knowledge_graph

# Extraction behavior
EXTRACTION_QUIET=1  # Set to 0 for verbose logging
EXTRACTION_PARALLEL_WORKERS=1  # Increase for parallel chunk processing

# Active LLM selection (overrides defaults)
ACTIVE_LLM=ds  # Options: ds, gemini3flash, gemini3pro, sonetto5high, sonetto_gemini3pro
```

## Key Design Patterns

### 1. LLM Configuration Resolution

Both `knowledge_extractor.py` and `agent.py` use `_resolve_llm_config()` to dynamically select LLM based on `ACTIVE_LLM` env var. This allows runtime switching between models without code changes.

### 2. Char Interval Traceability

All extractions maintain `char_interval: {start_pos, end_pos}` pointing to exact source text location. When chunking, chunk offsets are added to maintain global positions.

### 3. Robust LangExtract Integration

`knowledge_extractor.py` includes extensive patches:
- `_patch_langextract_json_parser()`: Strips markdown fences, fixes extraction_text type issues
- `_coerce_langextract_payload()`: Normalizes various JSON response formats
- `_repair_json_invalid_escapes()`: Fixes invalid escape sequences from some gateways
- Multiple retry strategies with different `force_json` and `fence_output` combinations

### 4. Knowledge Base Isolation

Each KB is completely isolated with its own:
- File storage directory
- ChromaDB collection (`kb_{kb_id}`)
- Graph JSON file
- Document artifacts

### 5. Session State Management

UI uses singleton `SessionState` class (`session.py`) to maintain:
- Current KB selection
- Document processing state
- UI logs buffer (auto-trimmed to last 500 lines)
- LLM configuration overrides

## Important Implementation Notes

### When Adding New Extraction Classes

1. Update prompt in `src/configs/prompts/` (e.g., `ziwei_doushu.py` or `general.py`)
2. Add examples to guide LLM output format
3. Update `InMemoryGraphStore.build_from_extractions()` if new class needs special graph handling
4. Test with `test_simple_extract.py`

### When Modifying Agent Behavior

- Agent system prompt in `agent.py:SYSTEM_PROMPT` enforces tool usage
- Tool call validation in `agent_query()` rejects responses without tool calls
- Evidence filtering removes references to deleted documents (best-effort cleanup)

### When Working with MinerU

- `parse_pdf_to_pages()` returns (pages, offsets, zip_bytes, full_markdown)
- Pages are 1-indexed in UI but 0-indexed in arrays
- HTML tables are auto-converted to markdown
- VPN/proxy issues handled via curl with `--noproxy` and DoH DNS resolution

### When Debugging Extraction Issues

1. Set `EXTRACTION_QUIET=0` for verbose logging
2. Check `outputs/knowledge_bases/{kb_id}/documents/{doc_id}/extractions.json`
3. Review UI logs in bottom expander panel
4. Use `debug_langextract.py` to test extraction in isolation
5. Check for `extraction_text` type errors (should be string, not dict/list)

### File Structure Conventions

- Knowledge bases: `outputs/knowledge_bases/{kb_id}/`
- Run artifacts (legacy): `outputs/runs/{run_id}/`
- ChromaDB: `./chroma_db/` (configurable via env)
- Agent logs: `outputs/logs/agent_chat_{date}.log`

## Domain-Specific: ZiWei DouShu

This codebase includes specialized extraction for ZiWei DouShu (紫微斗数) astrology documents:

- Custom prompt in `src/configs/prompts/ziwei_doushu.py`
- Extraction classes: 专业术语定义, 宫位关系网络, 星曜特性, 命理规则, 实战案例
- Special graph handling for 宫位关系网络 (palace relationship networks)
- Configurable via UI settings sidebar

## Common Pitfalls

1. **Don't bypass KnowledgeBaseService**: Always use `kb_service` for file operations to maintain consistency
2. **Don't forget to update graph after extraction**: Call `kb_service.merge_graph()` or `save_graph()`
3. **Don't assume extraction_text is always string**: Some models return dict/list, use type checking
4. **Don't hardcode collection names**: Use `kb_service.get_collection_name(kb_id)`
5. **Don't skip char_interval validation**: Some extractions may have None char_interval
6. **Agent must call tools**: System enforces evidence-based answers, no direct responses allowed

## OpenSpec Integration

This project uses OpenSpec for change management (see `openspec/` directory and `AGENTS.md`). When making architectural changes, follow the OpenSpec workflow for proposals and specs.
