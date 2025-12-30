import os
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from src.agents.tools import vector_search_tool, graph_search_tool, hybrid_search_tool, init_tools
from src.retrieval.vector.chroma_store import ChromaVectorStore
from src.graph.in_memory_store import InMemoryGraphStore

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek-chat")

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
    llm = ChatOpenAI(
        model=DEFAULT_MODEL,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        temperature=0.3,
    )
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
    
    result = _AGENT.invoke({
        "messages": [HumanMessage(content=question)]
    })
    
    # 提取最终回答
    answer = result["messages"][-1].content
    
    # 提取工具调用记录作为 evidence
    tool_calls = []
    for msg in result["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "type": "call",
                    "tool": tc.get("name", "unknown"),
                    "args": tc.get("args", {})
                })
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
