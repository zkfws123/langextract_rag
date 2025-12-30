# Knowledge Graph Specification

## ADDED Requirements

### Requirement: Entity and Relation Extraction
The system SHALL use LangExtract to extract entities and relations from parsed documents.

#### Scenario: Extract from Markdown
- **GIVEN** structured Markdown text from parsed PDF
- **WHEN** knowledge extraction is triggered
- **THEN** system SHALL use LangExtract with prompt and examples
- **AND** extract entities (人物、机构、地点、时间、概念)
- **AND** extract relations (合作、隶属、引用)
- **AND** preserve char_interval for every extraction

### Requirement: In-Memory Graph Storage
The system SHALL store knowledge graph as in-memory dictionary structure with JSON persistence.

#### Scenario: Build Graph from Extractions
- **GIVEN** LangExtract results with 50 entities and 30 relations
- **WHEN** graph construction is executed
- **THEN** system SHALL create entities dict with {entity_name: {type, attributes, mentions}}
- **AND** create relations list with {subject, predicate, object, attributes}
- **AND** save to JSON file at outputs/knowledge_graph.json
- **AND** load from JSON on next startup

### Requirement: Multi-hop Graph Search
The system SHALL implement graph traversal to find entities and relations within N hops.

#### Scenario: 1-hop Entity Search
- **GIVEN** knowledge graph with 100 entities
- **WHEN** user queries entity "清华大学" with hop=1
- **THEN** system SHALL fuzzy match "清华大学" in entity names
- **AND** find all relations where subject or object contains matched entity
- **AND** collect all connected entities (1-hop neighbors)
- **AND** return subgraph with entities and relations

#### Scenario: 2-hop Relation Discovery
- **GIVEN** entity "张三" connected to "清华大学" and "清华大学" connected to "AI研究院"
- **WHEN** user searches "张三" with hop=2
- **THEN** system SHALL find 1-hop neighbor "清华大学"
- **AND** recursively find 2-hop neighbors including "AI研究院"
- **AND** return complete path with intermediate relations

### Requirement: Graph Algorithms Integration
The system SHALL integrate networkx for community detection and centrality computation.

#### Scenario: Detect Communities
- **GIVEN** knowledge graph with 200 entities and 500 relations
- **WHEN** community detection is triggered
- **THEN** system SHALL convert to networkx Graph
- **AND** apply Louvain or Label Propagation algorithm
- **AND** identify densely connected clusters
- **AND** label entities with community_id

#### Scenario: Compute Entity Centrality
- **GIVEN** constructed networkx graph
- **WHEN** centrality metrics are requested
- **THEN** system SHALL compute degree centrality (节点度数)
- **AND** compute betweenness centrality (中介中心性)
- **AND** compute PageRank scores
- **AND** rank entities by importance

### Requirement: Source Traceability
The system SHALL maintain char_interval in entity mentions for complete traceability.

#### Scenario: Trace Entity to Source
- **GIVEN** entity "DeepSeek" with mentions=[{char_interval: {start: 234, end: 242}, doc_id: "test.pdf"}]
- **WHEN** user clicks on entity in graph visualization
- **THEN** system SHALL display all mention locations
- **AND** extract original text snippet from Markdown
- **AND** highlight exact position in source document

### Requirement: Neo4j Optional Upgrade
The system SHALL provide Neo4j adapter as optional backend for large-scale graphs.

#### Scenario: Migrate to Neo4j
- **GIVEN** in-memory graph exceeds 10K entities
- **WHEN** user enables Neo4j in configuration
- **THEN** system SHALL connect to Neo4j database
- **AND** export entities as nodes with labels and properties
- **AND** export relations as edges with relationship types
- **AND** use Cypher queries for graph traversal
- **AND** maintain backward compatibility with in-memory interface
