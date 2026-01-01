"""洞察分析标签页"""
import streamlit as st
from src.ui.session import SessionManager
from src.ui.components import render_insights
from src.knowledge_base import get_kb_service
from src.graph.models import KnowledgeExtraction


def render_insights_tab(session: SessionManager):
    """渲染抽取洞察标签页"""
    st.header("抽取洞察")
    
    if not session.current_kb_id or not session.current_doc_id:
        st.info("暂无选中的文档，请先在侧边栏选择文档")
        return
    
    kb_service = get_kb_service()
    markdown = kb_service.load_doc_markdown(session.current_kb_id, session.current_doc_id)
    extractions_data = kb_service.load_doc_extractions(session.current_kb_id, session.current_doc_id)
    
    if not markdown:
        st.info("暂无解析内容，请先点击“解析”按钮")
        return
    
    if not extractions_data:
        st.info("暂无提取结果，请先点击“提取”按钮")
        return
    
    extractions = [KnowledgeExtraction(**e) for e in extractions_data]
    
    with st.spinner("正在生成洞察分析..."):
        render_insights(markdown, extractions)
