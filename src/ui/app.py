"""
GraphRAG Streamlit UI - 知识库管理版本（模块化架构）
"""
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# 添加项目根目录到 path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=True)

from src.ui.session import get_session
from src.ui.kb_sidebar import render_kb_sidebar
from src.ui.doc_workflow import render_doc_workflow
from src.ui.settings_sidebar import render_settings_sidebar
from src.ui.tabs import (
    render_chat_tab,
    render_ocr_tab,
    render_preview_tab,
    render_graph_tab,
    render_extractions_tab,
    render_insights_tab,
)

# ============================================================================
# 页面配置
# ============================================================================
st.set_page_config(
    page_title="GraphRAG 知识问答系统",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# 初始化 Session
# ============================================================================
session = get_session()

# ============================================================================
# 侧边栏：知识库管理 + 文档工作流 + 设置
# ============================================================================
with st.sidebar:
    # 1. 知识库管理
    kb_service = render_kb_sidebar(session)
    
    # 2. 文档工作流
    render_doc_workflow(session, kb_service)
    
    # 3. 设置配置
    render_settings_sidebar(session)

# ============================================================================
# 主区域：标签页
# ============================================================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "问答",
    "OCR 对比",
    "解析预览",
    "知识图谱",
    "提取结果",
    "抽取洞察",
])

with tab1:
    render_chat_tab(session, kb_service)

with tab2:
    render_ocr_tab(session)

with tab3:
    render_preview_tab(session)

with tab4:
    render_graph_tab(session)

with tab5:
    render_extractions_tab(session)

with tab6:
    render_insights_tab(session)

# ============================================================================
# 页脚
# ============================================================================
st.divider()
st.caption("GraphRAG 知识问答系统 | Powered by LangExtract + ChromaDB + LangGraph")
