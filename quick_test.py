#!/usr/bin/env python
"""Quick smoke test for knowledge extraction pipeline."""

from pathlib import Path
from src.parsers.knowledge_extractor import KnowledgeExtractor, ingest_text_file, search_knowledge
from src.retrieval.vector.chroma_store import ChromaVectorStore
from src.graph.in_memory_store import InMemoryGraphStore

# Test text
test_text = """
# AI 研究进展

2024年，DeepSeek发布了最新的大语言模型。
清华大学与北京大学合作开展了人工智能研究。
研究显示模型准确率提升了25%。
"""

def main():
    print("=" * 80)
    print("🚀 Knowledge Extraction Pipeline Smoke Test")
    print("=" * 80)
    
    # Step 1: Initialize stores
    print("\n[1/4] Initializing stores...")
    vector_store = ChromaVectorStore()
    graph_store = InMemoryGraphStore()
    print("  ✓ Vector store initialized")
    print("  ✓ Graph store initialized")
    
    # Step 2: Extract knowledge
    print("\n[2/4] Extracting knowledge with LangExtract...")
    extractor = KnowledgeExtractor(doc_id="test_001", doc_title="AI研究进展")
    extractions = extractor.extract_from_text(test_text)
    print(f"  ✓ Extracted {len(extractions)} items")
    
    # Step 3: Populate stores
    print("\n[3/4] Populating stores...")
    vector_store.index_extractions(extractions)
    graph_store.build_from_extractions(extractions)
    print(f"  ✓ Vector store: {len(extractions)} items indexed")
    print(f"  ✓ Graph store: {len(graph_store.knowledge_graph['entities'])} entities, "
          f"{len(graph_store.knowledge_graph['relations'])} relations")
    
    # Step 4: Test search
    print("\n[4/4] Testing search...")
    query = "人工智能研究"
    results = search_knowledge(query, vector_store, graph_store, top_k=3)
    
    print(f"\n  Query: '{query}'")
    
    vector_results = results.get("vector_results", [])
    graph_results = results.get("graph_results", {})
    
    if vector_results and len(vector_results) > 0:
        print(f"  Vector results: {len(vector_results)}")
        print("\n  Sample vector result:")
        r = vector_results[0]
        print(f"    Class: {r['extraction_class']}")
        print(f"    Text: {r['extraction_text']}")
        if r.get('char_interval'):
            print(f"    Position: {r['char_interval']['start_pos']}-{r['char_interval']['end_pos']}")
    else:
        print(f"  No vector results found")
    
    if graph_results:
        print(f"\n  Graph results: {len(graph_results.get('matched_entities', []))} matched entities")
    
    print("\n" + "=" * 80)
    print("✅ Smoke test completed successfully!")
    print("=" * 80)

if __name__ == "__main__":
    main()
