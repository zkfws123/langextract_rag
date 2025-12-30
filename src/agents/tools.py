from typing import Optional

from langchain.tools import tool

from src.retrieval.vector.chroma_store import ChromaVectorStore
from src.graph.in_memory_store import InMemoryGraphStore


_VECTOR_STORE: Optional[ChromaVectorStore] = None
_GRAPH_STORE: Optional[InMemoryGraphStore] = None


def init_tools(vector_store: ChromaVectorStore, graph_store: InMemoryGraphStore) -> None:
    global _VECTOR_STORE, _GRAPH_STORE
    _VECTOR_STORE = vector_store
    _GRAPH_STORE = graph_store


@tool
def vector_search_tool(query: str) -> str:
    """在向量数据库中搜索与查询相关的知识片段。用于语义相似度检索。"""
    if not _VECTOR_STORE:
        return "向量库未初始化"
    results = _VECTOR_STORE.similarity_search(query, top_k=5)
    if not results:
        return "未找到相关信息"
    output_parts = []
    for i, r in enumerate(results, 1):
        part = f"[V{i}] {r.get('extraction_class')}: {r.get('extraction_text')}"
        interval = r.get("char_interval")
        if interval:
            part += f"\n     位置: 字符 {interval.get('start_pos')}-{interval.get('end_pos')}"
        part += f"\n     来源: {r.get('doc_title')}"
        attrs = r.get("attributes")
        if attrs:
            part += f"\n     属性: {attrs}"
        output_parts.append(part)
    return "\n\n".join(output_parts)


@tool
def graph_search_tool(entity: str) -> str:
    """在知识图谱中搜索实体及其关联关系。用于结构化知识查询。"""
    if not _GRAPH_STORE:
        return "知识图谱未初始化"
    results = _GRAPH_STORE.search(entity, hop=1)
    lines = []
    if results.get("matched_entities"):
        lines.append("匹配实体:")
        for name, data in results["matched_entities"]:
            lines.append(f"- {name} | 类型: {data.get('type')} | 属性: {data.get('attributes')}")
    if results.get("related_relations"):
        lines.append("\n关联关系:")
        for rel in results["related_relations"]:
            lines.append(
                f"- {rel.get('subject')} -[{rel.get('relation') or rel.get('type')}]-> {rel.get('object')}"
            )
    if results.get("connected_entities"):
        lines.append("\n关联实体:")
        for ent in results["connected_entities"]:
            lines.append(f"- {ent}")
    return "\n".join(lines) if lines else "未找到相关信息"


@tool
def hybrid_search_tool(query: str) -> str:
    """混合检索工具，同时使用向量检索和图谱检索获取更全面的结果。"""
    if not _VECTOR_STORE or not _GRAPH_STORE:
        return "混合检索组件未初始化"
    vector_result = vector_search_tool.invoke(query)
    words = [w for w in query.replace("？", "").replace("?", "").replace("，", " ").replace("。", " ").split() if len(w) >= 2]
    graph_results = []
    for word in words[:3]:
        gr = graph_search_tool.invoke(word)
        if "未找到" not in gr and gr:
            graph_results.append(gr)
    output = "=== 向量检索结果 ===\n" + vector_result
    if graph_results:
        output += "\n\n=== 图谱检索结果 ===\n" + "\n".join(graph_results)
    return output
