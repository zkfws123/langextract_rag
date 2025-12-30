# Hybrid Retrieval Specification

## ADDED Requirements

### Requirement: Multi-route Recall System
The system SHALL implement multi-route recall combining vector search, full-text search, and graph search.

#### Scenario: Execute Hybrid Search
- **GIVEN** a user query "什么是知识图谱?"
- **WHEN** hybrid search is triggered
- **THEN** system SHALL execute vector search using ChromaDB/FAISS
- **AND** execute BM25 full-text search
- **AND** execute graph search for related entities
- **AND** combine all results with unique IDs

### Requirement: Reciprocal Rank Fusion (RRF)
The system SHALL use RRF algorithm to merge and rerank results from multiple retrievers.

#### Scenario: Rerank Mixed Results
- **GIVEN** 10 results from vector search (scores 0.9-0.7)
- **AND** 8 results from BM25 (scores 5.2-2.1)
- **AND** 5 results from graph search
- **WHEN** RRF reranking is applied
- **THEN** system SHALL convert all scores to reciprocal ranks
- **AND** aggregate ranks with configurable weights
- **AND** return top-K results sorted by combined score

### Requirement: Vector Search Integration
The system SHALL support multiple vector store backends (ChromaDB, FAISS, Milvus).

#### Scenario: Switch Vector Backend
- **GIVEN** configuration specifies FAISS as vector store
- **WHEN** system initializes retrieval
- **THEN** system SHALL load FAISS index from disk
- **AND** use阿里云百炼 text-embedding-v4 for query encoding
- **AND** execute cosine similarity search
- **AND** return top_k results with similarity scores

### Requirement: BM25 Full-text Search
The system SHALL implement BM25 algorithm for keyword-based retrieval.

#### Scenario: Execute BM25 Search
- **GIVEN** indexed documents with tokenized content
- **WHEN** user query contains specific keywords
- **THEN** system SHALL tokenize query
- **AND** compute BM25 scores for all documents
- **AND** return ranked results with term frequency highlights

### Requirement: Graph-enhanced Retrieval
The system SHALL retrieve entities and relations from knowledge graph to augment search results.

#### Scenario: Multi-hop Graph Search
- **GIVEN** query mentions entity "DeepSeek"
- **WHEN** graph search is executed with hop=2
- **THEN** system SHALL find "DeepSeek" entity in graph
- **AND** retrieve all 1-hop relations (直接关联)
- **AND** retrieve all 2-hop relations (二度关联)
- **AND** return subgraph with entities and relations

### Requirement: Result Deduplication
The system SHALL deduplicate results from multiple retrievers based on document ID and content similarity.

#### Scenario: Remove Duplicate Results
- **GIVEN** vector search returns doc_id="abc123"
- **AND** BM25 also returns doc_id="abc123"
- **WHEN** results are combined
- **THEN** system SHALL keep only one copy
- **AND** merge metadata from both sources
- **AND** retain highest score

### Requirement: Source Attribution
The system SHALL preserve char_interval for every retrieved result to enable source tracing.

#### Scenario: Trace Result to Original Text
- **GIVEN** a retrieved extraction with char_interval={start: 1234, end: 1456}
- **WHEN** user requests source verification
- **THEN** system SHALL locate original Markdown text
- **AND** extract substring from position 1234 to 1456
- **AND** highlight the exact source text
- **AND** display context (100 chars before/after)
