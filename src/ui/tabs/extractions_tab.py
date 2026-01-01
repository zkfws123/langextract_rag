"""提取结果标签页"""
import streamlit as st
from src.ui.session import SessionManager
from src.knowledge_base import get_kb_service
from src.graph.models import KnowledgeExtraction


def render_extractions_tab(session: SessionManager):
    """渲染知识提取结果标签页"""
    st.header("知识提取结果")
    
    if not session.current_kb_id or not session.current_doc_id:
        st.info("暂无选中的文档，请先在侧边栏选择文档")
        return
    
    kb_service = get_kb_service()
    extractions_data = kb_service.load_doc_extractions(session.current_kb_id, session.current_doc_id)
    
    if not extractions_data:
        st.info("暂无提取结果，请先点击“提取”按钮")
        return
    
    extractions = [KnowledgeExtraction(**e) for e in extractions_data]
    
    # 分类统计
    class_counts = {}
    for ext in extractions:
        cls = ext.extraction_class
        class_counts[cls] = class_counts.get(cls, 0) + 1
    
    st.subheader("分类统计")
    cols = st.columns(len(class_counts))
    for i, (cls, count) in enumerate(class_counts.items()):
        with cols[i]:
            st.metric(cls, count)
    
    st.divider()
    
    # 详细列表
    st.subheader("详细列表")
    filter_class = st.selectbox("按类别筛选", ["全部"] + list(class_counts.keys()))
    
    for i, ext in enumerate(extractions):
        if filter_class != "全部" and ext.extraction_class != filter_class:
            continue
        
        with st.expander(f"[{ext.extraction_class}] {ext.extraction_text[:50]}..."):
            st.markdown(f"**类别**: {ext.extraction_class}")
            st.markdown(f"**原文**: {ext.extraction_text}")
            if ext.char_interval:
                start = ext.char_interval.get('start_pos', '?')
                end = ext.char_interval.get('end_pos', '?')
                st.markdown(f"**位置**: 字符 {start} - {end}")
            if ext.attributes:
                st.markdown("**属性**:")
                st.json(ext.attributes)
