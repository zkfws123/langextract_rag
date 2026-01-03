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
from src.ui.ui_logger import setup_ui_logger
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
# iOS-ish theme: soft background, cards, subtle borders, better typography
# ============================================================================
st.markdown(
        """
        <style>
            :root {
                --ios-bg: #0e1117;
                --ios-card: rgba(17, 24, 39, 0.78);
                --ios-border: rgba(148, 163, 184, 0.18);
                --ios-text: rgba(255, 255, 255, 0.92);
                --ios-muted: rgba(255, 255, 255, 0.64);
                --ios-primary: #0A84FF;
                --ios-primary-2: #7C3AED;
            }

            .stApp {
                background: radial-gradient(1200px 900px at 10% 0%, rgba(10,132,255,0.14), transparent 60%),
                                        radial-gradient(1100px 800px at 90% 10%, rgba(124,58,237,0.14), transparent 62%),
                                        var(--ios-bg) !important;
                color: var(--ios-text) !important;
            }

            /* Make main container feel like a card */
            section.main > div {
                padding-top: 0.25rem;
            }

            /* Sidebar polish */
            section[data-testid="stSidebar"] {
                background: linear-gradient(180deg, rgba(17,24,39,0.86), rgba(17,24,39,0.72)) !important;
                border-right: 1px solid var(--ios-border) !important;
                backdrop-filter: blur(14px);
            }

            /* Expander card look */
            div[data-testid="stExpander"] {
                border: 1px solid var(--ios-border) !important;
                border-radius: 14px !important;
                background: var(--ios-card) !important;
                box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
            }

            /* Inputs */
            input, textarea {
                border-radius: 12px !important;
            }

            /* Tabs - slightly round */
            div[data-baseweb="tab"] {
                border-radius: 999px !important;
            }

            /* Captions */
            .stCaption {
                color: var(--ios-muted) !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
)

# ============================================================================
# 全局样式：美化按钮选中态（primary）
# ============================================================================
st.markdown(
        """
        <style>
            /* Base button shape */
            .stButton > button {
                border-radius: 999px !important;
                padding: 0.45rem 0.85rem !important;
                font-weight: 600 !important;
                border: 1px solid rgba(148, 163, 184, 0.35) !important; /* slate-400 */
                transition: transform 120ms ease, box-shadow 160ms ease, background-color 160ms ease, border-color 160ms ease;
                box-shadow: 0 1px 0 rgba(15, 23, 42, 0.06) !important;
            }

            /* Secondary (unselected) */
            .stButton > button[kind="secondary"] {
                background: rgba(255, 255, 255, 0.06) !important;
                color: rgba(255, 255, 255, 0.88) !important;
            }
            .stButton > button[kind="secondary"]:hover {
                background: rgba(255, 255, 255, 0.10) !important;
                border-color: rgba(148, 163, 184, 0.55) !important;
                transform: translateY(-1px);
                box-shadow: 0 8px 22px rgba(15, 23, 42, 0.22) !important;
            }

            /* Primary (selected) */
            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%) !important; /* blue-600 -> violet-600 */
                border-color: rgba(37, 99, 235, 0.45) !important;
                color: #ffffff !important;
                box-shadow: 0 10px 26px rgba(37, 99, 235, 0.28), 0 2px 0 rgba(15, 23, 42, 0.08) !important;
            }
            .stButton > button[kind="primary"]:hover {
                transform: translateY(-1px);
                box-shadow: 0 14px 30px rgba(124, 58, 237, 0.30), 0 10px 22px rgba(37, 99, 235, 0.18) !important;
                filter: brightness(1.02);
            }
            .stButton > button:active {
                transform: translateY(0px) scale(0.99);
            }

            /* Better focus ring */
            .stButton > button:focus {
                outline: none !important;
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25), 0 10px 26px rgba(37, 99, 235, 0.22) !important;
            }

            /* Sidebar buttons a bit tighter to look like list selection chips */
            section[data-testid="stSidebar"] .stButton > button {
                padding: 0.36rem 0.65rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
)

# ============================================================================
# 初始化 Session
# ============================================================================
session = get_session()

# 初始化 UI 日志捕获（写入 session_state.ui_logs）
setup_ui_logger()

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
# 日志面板（底部可折叠）
# ============================================================================
with st.expander("🧾 运行日志", expanded=False):
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.caption("显示提取/关系抽取/入库等流程的开始-结束日志（自动滚动保存最近 N 行）。")
    with col_b:
        if st.button("清空日志", use_container_width=True):
            session.ui_logs_clear()
            st.rerun()

    logs = session.ui_logs
    if not logs:
        st.info("暂无日志")
    else:
        st.code("\n".join(logs[-500:]), language="text")

# ============================================================================
# 页脚
# ============================================================================
st.divider()
st.caption("GraphRAG 知识问答系统 | Powered by LangExtract + ChromaDB + LangGraph")
