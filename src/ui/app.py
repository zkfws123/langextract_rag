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
                background: rgba(15, 23, 42, 0.06) !important;
                color: rgba(15, 23, 42, 0.86) !important;
            }
            .stButton > button[kind="secondary"]:hover {
                background: rgba(15, 23, 42, 0.09) !important;
                border-color: rgba(148, 163, 184, 0.55) !important;
                transform: translateY(-1px);
                box-shadow: 0 8px 22px rgba(15, 23, 42, 0.12) !important;
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
