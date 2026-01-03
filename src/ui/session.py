"""Session State 管理器 - 分组管理所有状态"""
from typing import Optional, List, Any
import streamlit as st

from src.graph.in_memory_store import InMemoryGraphStore
from src.graph.models import KnowledgeExtraction
from src.retrieval.vector.chroma_store import ChromaVectorStore


class SessionManager:
    """统一管理 Streamlit Session State"""
    
    def __init__(self):
        self._init_all_states()
    
    def _init_all_states(self):
        """初始化所有状态"""
        # 知识库状态
        if "current_kb_id" not in st.session_state:
            st.session_state.current_kb_id = ""
        if "kb_list_cache" not in st.session_state:
            st.session_state.kb_list_cache = []
        
        # 文档状态
        if "current_doc_id" not in st.session_state:
            st.session_state.current_doc_id = ""
        if "doc_list_cache" not in st.session_state:
            st.session_state.doc_list_cache = []
        if "pdf_bytes" not in st.session_state:
            st.session_state.pdf_bytes = b""
        if "uploaded_filename" not in st.session_state:
            st.session_state.uploaded_filename = ""
        if "markdown_content" not in st.session_state:
            st.session_state.markdown_content = ""
        if "markdown_pages" not in st.session_state:
            st.session_state.markdown_pages = []
        if "page_offsets" not in st.session_state:
            st.session_state.page_offsets = []
        
        # 提取状态
        if "extractions" not in st.session_state:
            st.session_state.extractions = []
        if "extraction_prompt" not in st.session_state:
            st.session_state.extraction_prompt = ""
        if "extraction_examples_json" not in st.session_state:
            st.session_state.extraction_examples_json = ""
        if "extraction_examples_parsed" not in st.session_state:
            st.session_state.extraction_examples_parsed = []
        if "selected_doc_type" not in st.session_state:
            from src.configs import ConfigType
            st.session_state.selected_doc_type = ConfigType.ZIWEI_DOUSHU

        # 并行提取设置（UI 控制）
        if "extraction_parallel_enabled" not in st.session_state:
            st.session_state.extraction_parallel_enabled = False
        if "extraction_parallel_workers" not in st.session_state:
            st.session_state.extraction_parallel_workers = 4

        # UI 日志缓冲（给前端日志面板用）
        if "ui_logs" not in st.session_state:
            st.session_state.ui_logs = []
        if "ui_logs_max_lines" not in st.session_state:
            st.session_state.ui_logs_max_lines = 500
        
        # 图谱和向量库
        if "graph_store" not in st.session_state:
            st.session_state.graph_store = InMemoryGraphStore()
        if "vector_store" not in st.session_state:
            st.session_state.vector_store = None
        
        # Agent 状态
        if "agent_built" not in st.session_state:
            st.session_state.agent_built = False
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        
        # UI 状态
        if "current_page_num" not in st.session_state:
            st.session_state.current_page_num = 1
        if "active_llm" not in st.session_state:
            import os
            # 默认使用 sonetto5high
            st.session_state.active_llm = os.getenv("ACTIVE_LLM") or "sonetto5high"

        # 统一 UI 选择与底层提取/Agent 读取的环境变量
        import os
        os.environ["ACTIVE_LLM"] = st.session_state.active_llm
    
    # ========== 知识库状态 ==========
    
    @property
    def current_kb_id(self) -> str:
        # Be defensive: Streamlit can execute modules in an order where
        # properties are accessed before our initializer ran for a new session.
        return st.session_state.get("current_kb_id", "")

    @current_kb_id.setter
    def current_kb_id(self, value: str):
        st.session_state.current_kb_id = value
    
    @property
    def kb_list_cache(self) -> List[Any]:
        return st.session_state.kb_list_cache
    
    @kb_list_cache.setter
    def kb_list_cache(self, value: List[Any]):
        st.session_state.kb_list_cache = value
    
    # ========== 文档状态 ==========
    
    @property
    def current_doc_id(self) -> str:
        return st.session_state.current_doc_id
    
    @current_doc_id.setter
    def current_doc_id(self, value: str):
        st.session_state.current_doc_id = value
    
    @property
    def doc_list_cache(self) -> List[Any]:
        return st.session_state.doc_list_cache
    
    @doc_list_cache.setter
    def doc_list_cache(self, value: List[Any]):
        st.session_state.doc_list_cache = value
    
    @property
    def pdf_bytes(self) -> bytes:
        return st.session_state.pdf_bytes
    
    @pdf_bytes.setter
    def pdf_bytes(self, value: bytes):
        st.session_state.pdf_bytes = value
    
    @property
    def uploaded_filename(self) -> str:
        return st.session_state.uploaded_filename
    
    @uploaded_filename.setter
    def uploaded_filename(self, value: str):
        st.session_state.uploaded_filename = value
    
    @property
    def markdown_content(self) -> str:
        return st.session_state.markdown_content
    
    @markdown_content.setter
    def markdown_content(self, value: str):
        st.session_state.markdown_content = value
    
    @property
    def markdown_pages(self) -> List[str]:
        return st.session_state.markdown_pages
    
    @markdown_pages.setter
    def markdown_pages(self, value: List[str]):
        st.session_state.markdown_pages = value
    
    @property
    def page_offsets(self) -> List[int]:
        return st.session_state.page_offsets
    
    @page_offsets.setter
    def page_offsets(self, value: List[int]):
        st.session_state.page_offsets = value
    
    # ========== 提取状态 ==========
    
    @property
    def extractions(self) -> List[KnowledgeExtraction]:
        return st.session_state.extractions
    
    @extractions.setter
    def extractions(self, value: List[KnowledgeExtraction]):
        st.session_state.extractions = value
    
    @property
    def extraction_prompt(self) -> str:
        return st.session_state.extraction_prompt
    
    @extraction_prompt.setter
    def extraction_prompt(self, value: str):
        st.session_state.extraction_prompt = value
    
    @property
    def extraction_examples_json(self) -> str:
        return st.session_state.extraction_examples_json
    
    @extraction_examples_json.setter
    def extraction_examples_json(self, value: str):
        st.session_state.extraction_examples_json = value
    
    @property
    def extraction_examples_parsed(self) -> List[dict]:
        return st.session_state.extraction_examples_parsed
    
    @extraction_examples_parsed.setter
    def extraction_examples_parsed(self, value: List[dict]):
        st.session_state.extraction_examples_parsed = value
    
    @property
    def selected_doc_type(self):
        return st.session_state.selected_doc_type
    
    @selected_doc_type.setter
    def selected_doc_type(self, value):
        st.session_state.selected_doc_type = value

    # ========== 并行提取设置 ==========

    @property
    def extraction_parallel_enabled(self) -> bool:
        return bool(st.session_state.get("extraction_parallel_enabled", False))

    @extraction_parallel_enabled.setter
    def extraction_parallel_enabled(self, value: bool):
        st.session_state.extraction_parallel_enabled = bool(value)

    @property
    def extraction_parallel_workers(self) -> int:
        try:
            return int(st.session_state.get("extraction_parallel_workers", 4))
        except Exception:
            return 4

    @extraction_parallel_workers.setter
    def extraction_parallel_workers(self, value: int):
        try:
            st.session_state.extraction_parallel_workers = int(value)
        except Exception:
            st.session_state.extraction_parallel_workers = 4

    # ========== UI 日志 ==========

    @property
    def ui_logs(self) -> List[str]:
        return st.session_state.ui_logs

    @property
    def ui_logs_max_lines(self) -> int:
        return int(st.session_state.get("ui_logs_max_lines", 500))

    def ui_log(self, message: str) -> None:
        """Append one log line to the UI buffer (ring buffer)."""
        msg = str(message)
        st.session_state.ui_logs.append(msg)
        max_lines = self.ui_logs_max_lines
        if max_lines and len(st.session_state.ui_logs) > max_lines:
            st.session_state.ui_logs = st.session_state.ui_logs[-max_lines:]

    def ui_logs_clear(self) -> None:
        st.session_state.ui_logs = []
    
    # ========== 图谱和向量库 ==========
    
    @property
    def graph_store(self) -> InMemoryGraphStore:
        return st.session_state.graph_store
    
    @graph_store.setter
    def graph_store(self, value: InMemoryGraphStore):
        st.session_state.graph_store = value
    
    @property
    def vector_store(self) -> Optional[ChromaVectorStore]:
        return st.session_state.vector_store
    
    @vector_store.setter
    def vector_store(self, value: Optional[ChromaVectorStore]):
        st.session_state.vector_store = value
    
    # ========== Agent 状态 ==========
    
    @property
    def agent_built(self) -> bool:
        return st.session_state.agent_built
    
    @agent_built.setter
    def agent_built(self, value: bool):
        st.session_state.agent_built = value
    
    @property
    def chat_history(self) -> List[dict]:
        return st.session_state.chat_history
    
    @chat_history.setter
    def chat_history(self, value: List[dict]):
        st.session_state.chat_history = value
    
    # ========== UI 状态 ==========
    
    @property
    def current_page_num(self) -> int:
        return st.session_state.current_page_num
    
    @current_page_num.setter
    def current_page_num(self, value: int):
        st.session_state.current_page_num = value
    
    @property
    def active_llm(self) -> str:
        return st.session_state.active_llm
    
    @active_llm.setter
    def active_llm(self, value: str):
        st.session_state.active_llm = value
    
    # ========== 重置方法 ==========
    
    def reset_document_state(self):
        """重置文档相关状态"""
        self.current_doc_id = ""
        self.pdf_bytes = b""
        self.uploaded_filename = ""
        self.markdown_content = ""
        self.markdown_pages = []
        self.page_offsets = []
        self.extractions = []
        self.current_page_num = 1
    
    def reset_chat(self):
        """重置聊天历史"""
        self.chat_history = []
        self.agent_built = False
    
    def switch_kb(self, kb_id: str):
        """切换知识库（重置相关状态）"""
        self.current_kb_id = kb_id
        self.reset_document_state()
        self.reset_chat()
        self.vector_store = None
        self.graph_store = InMemoryGraphStore()


# 全局单例
_session_manager: Optional[SessionManager] = None

def get_session() -> SessionManager:
    """获取 Session 管理器单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    else:
        # Streamlit may create a fresh session_state on reruns/new browser sessions;
        # ensure required keys exist even when reusing the singleton.
        _session_manager._init_all_states()
    return _session_manager
