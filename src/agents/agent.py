import os
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from src.agents.tools import vector_search_tool, graph_search_tool, hybrid_search_tool, init_tools
from src.retrieval.vector.chroma_store import ChromaVectorStore
from src.graph.in_memory_store import InMemoryGraphStore

load_dotenv(override=True)


def _resolve_llm_config() -> tuple[str, str, str]:
    """Resolve (api_key, base_url, model_id) at call time.

    Supports UI override via ACTIVE_LLM in {ds, gemini3flash, gemini3pro, sonetto5high, sonetto_gemini3pro}.
    """

    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    default_model = os.getenv("DEFAULT_MODEL", "deepseek-chat")

    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    gemini_base_url = os.getenv("GEMINI_BASE_URL", "")
    gemini_model = os.getenv("GEMINI_MODEL", "")

    sonetto_api_key = os.getenv("SONETTO_API_KEY", "")
    sonetto_base_url = os.getenv("SONETTO_BASE_URL", "")
    sonetto_model_high = os.getenv("SONETTO_MODEL_HIGH", "")
    sonetto_model_gemini = os.getenv("SONETTO_MODEL_GEMINI", "")

    active = (os.getenv("ACTIVE_LLM", "") or "").strip().lower()
    if active == "ds":
        return deepseek_api_key, deepseek_base_url, default_model
    if active == "gemini3flash":
        return gemini_api_key, gemini_base_url, "gemini-3-flash-preview"
    if active == "gemini3pro":
        return gemini_api_key, gemini_base_url, "gemini-3-pro-preview"
    if active == "sonetto5high":
        return sonetto_api_key, sonetto_base_url, sonetto_model_high
    if active == "sonetto_gemini3pro":
        return sonetto_api_key, sonetto_base_url, sonetto_model_gemini

    # Default behavior: prefer Gemini config if provided.
    api_key = gemini_api_key or deepseek_api_key
    base_url = gemini_base_url or deepseek_base_url
    model_id = gemini_model or default_model
    return api_key, base_url, model_id

SYSTEM_PROMPT = """你是一个 GraphRAG 知识图谱问答助手。

你有以下工具可用：
1. vector_search_tool - 向量语义检索，找语义相关内容
2. graph_search_tool - 图谱关系检索，查实体及关联
3. hybrid_search_tool - 混合检索，向量+图谱组合

使用步骤：
- 先阅读用户问题，提取关键实体或概念
- 优先调用 hybrid_search_tool 获取综合结果
- 如需更多语义证据，可调用 vector_search_tool
- 如需关系链路，可调用 graph_search_tool
- 最终回答需要结合检索结果，并标注来源信息
"""

_AGENT = None


def build_agent(vector_store: Optional[ChromaVectorStore], graph_store: Optional[InMemoryGraphStore]):
    global _AGENT
    if vector_store and graph_store:
        init_tools(vector_store, graph_store)
    
    api_key, base_url, model_id = _resolve_llm_config()
    
    llm = ChatOpenAI(
        model=model_id,
        api_key=api_key,
        base_url=base_url,
        temperature=0.3,
    )
    
    # 使用 langchain 1.0.5 的 create_agent
    _AGENT = create_agent(
        model=llm,
        tools=[vector_search_tool, graph_search_tool, hybrid_search_tool],
        system_prompt=SYSTEM_PROMPT,
    )
    
    return _AGENT


def agent_query(question: str) -> Dict[str, Any]:
    """
    GraphRAG Agent 问答
    
    Args:
        question: 用户问题
    
    Returns:
        包含 question, answer, evidence 的字典
    """
    if not _AGENT:
        return {
            "question": question,
            "answer": "Agent 未初始化，请先调用 build_agent()",
            "evidence": []
        }
    
    from langchain_core.messages import HumanMessage
    
    # langchain 1.0.5 create_agent 返回的是 CompiledStateGraph
    result = _AGENT.invoke({
        "messages": [HumanMessage(content=question)]
    })
    
    # 提取最终回答
    messages = result.get("messages", [])
    answer = messages[-1].content if messages else "无法回答"
    
    # 提取工具调用记录作为 evidence
    tool_calls = []
    for msg in messages:
        # 检查是否是工具调用消息
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "type": "call",
                    "tool": tc.get("name", "unknown"),
                    "args": tc.get("args", {})
                })
        # 检查是否是工具返回消息
        if hasattr(msg, "name") and msg.name:
            tool_calls.append({
                "type": "result",
                "tool": msg.name,
                "content": msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
            })
    
    return {
        "question": question,
        "answer": answer,
        "evidence": tool_calls
    }
