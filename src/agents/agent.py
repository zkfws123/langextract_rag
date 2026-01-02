import os
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from src.agents.tools import vector_search_tool, graph_search_tool, hybrid_search_tool, init_tools
from src.retrieval.vector.chroma_store import ChromaVectorStore
from src.graph.in_memory_store import InMemoryGraphStore
from src.utils.logger import get_agent_logger

load_dotenv(override=True)

# 获取日志器
_logger = get_agent_logger()


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

🚨 【强制规则 - 违反将导致回答被拒绝】🚨

1. ⛔ 禁止直接回答：你绝对不允许在不调用工具的情况下直接回答任何问题
2. ✅ 必须调用工具：对于任何用户问题，你必须先调用 hybrid_search_tool 获取证据
3. 📋 基于证据回答：你的回答必须完全基于工具返回的证据，不得凭空编造
4. 🔍 工具返回空：如果工具返回"未找到相关信息"，你必须如实告知用户，不得编造内容
5. 📎 标注来源：回答中必须引用证据来源（文档名、位置等）

⚠️ 重要提醒：
- 即使问题看起来"很简单"，也必须调用工具查询知识库
- 即使你"知道答案"，也必须从知识库获取证据
- 不调用工具的回答将被系统自动拒绝并标记为错误

你有以下工具可用：
1. hybrid_search_tool - 混合检索（向量+图谱），优先使用
2. vector_search_tool - 向量语义检索，找语义相关内容
3. graph_search_tool - 图谱关系检索，查实体及关联

标准工作流程：
步骤1：收到用户问题
步骤2：立即调用 hybrid_search_tool(用户问题)
步骤3：分析工具返回的证据
步骤4：基于证据组织回答，并标注来源
步骤5：如果证据不足，可以再调用其他工具补充
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
    # 记录用户提问
    _logger.log_user_query(question)

    if not _AGENT:
        _logger.error("Agent未初始化")
        return {
            "question": question,
            "answer": "Agent 未初始化，请先调用 build_agent()",
            "evidence": []
        }

    from langchain_core.messages import HumanMessage

    try:
        # langchain 1.0.5 create_agent 返回的是 CompiledStateGraph
        _logger.info("开始调用Agent处理问题...")
        result = _AGENT.invoke({
            "messages": [HumanMessage(content=question)]
        })

        # --- 追因日志：记录返回结构与消息摘要（用于解释为何不产生 tool_calls） ---
        try:
            msg_count = len(result.get("messages", []) or [])
            _logger.debug(f"[trace] agent.invoke result keys: {list(result.keys())}")
            _logger.debug(f"[trace] agent.invoke messages count: {msg_count}")
        except Exception:
            pass

        # 提取最终回答
        messages = result.get("messages", [])
        answer = messages[-1].content if messages else "无法回答"

        # 提取工具调用记录作为 evidence
        tool_calls = []
        used_tools = set()

        for idx, msg in enumerate(messages):
            # 基础字段（不同 Message 类型字段不一，做 best-effort 摘要）
            try:
                msg_type = type(msg).__name__
                role = getattr(msg, "type", None) or getattr(msg, "role", None) or ""
                name = getattr(msg, "name", None) or ""
                content_preview = (getattr(msg, "content", "") or "")
                if isinstance(content_preview, str) and len(content_preview) > 160:
                    content_preview = content_preview[:160] + "..."
                _logger.debug(
                    f"[trace] msg[{idx}] type={msg_type} role={role} name={name} has_tool_calls={bool(getattr(msg, 'tool_calls', None))} content={content_preview}"
                )
            except Exception:
                pass

            # 检查是否是工具调用消息
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get("name", "unknown")
                    used_tools.add(tool_name)
                    tool_calls.append({
                        "type": "call",
                        "tool": tool_name,
                        "args": tc.get("args", {})
                    })
            # 检查是否是工具返回消息
            if hasattr(msg, "name") and msg.name:
                tool_calls.append({
                    "type": "result",
                    "tool": msg.name,
                    "content": msg.content[:500] + "..." if len(msg.content) > 500 else msg.content
                })

        # 记录Agent回答和工具使用情况
        _logger.log_agent_response(answer, list(used_tools))

        # 强制要求：必须调用知识库工具，否则报错
        if not used_tools:
            _logger.log_no_tool_warning()
            _logger.error("❌ 错误: Agent未调用任何知识库工具，违反证据溯源规则！")
            _logger.info("=" * 80)
            return {
                "question": question,
                "answer": "❌ 错误：Agent未调用知识库工具，无法提供可靠答案。请重新提问或换个问法。",
                "evidence": [],
                "error": "NO_TOOL_CALLED"
            }

        _logger.info("=" * 80)

        return {
            "question": question,
            "answer": answer,
            "evidence": tool_calls
        }

    except Exception as e:
        _logger.error(f"Agent查询出错: {str(e)}")
        _logger.info("=" * 80)
        return {
            "question": question,
            "answer": f"查询出错: {str(e)}",
            "evidence": []
        }
