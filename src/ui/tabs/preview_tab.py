"""解析预览标签页"""
import streamlit as st
from src.ui.session import SessionManager
from src.knowledge_base import get_kb_service


def render_preview_tab(session: SessionManager):
    """渲染 PDF 解析预览标签页"""
    st.header("PDF 解析结果")
    
    if not session.current_kb_id or not session.current_doc_id:
        st.info("暂无选中的文档，请先在侧边栏选择文档")
        return
    
    kb_service = get_kb_service()
    markdown = kb_service.load_doc_markdown(session.current_kb_id, session.current_doc_id)
    
    if markdown:
        st.markdown(markdown[:10000])
        if len(markdown) > 10000:
            st.info(f"内容过长，仅显示前 10000 字符 (共 {len(markdown):,} 字符)")
    else:
        st.info("暂无解析内容，请先点击“解析”按钮")
