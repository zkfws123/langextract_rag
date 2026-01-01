"""OCR 对比标签页"""
import streamlit as st
from src.ui.session import SessionManager
from src.ui.components import render_pdf_viewer
from src.knowledge_base import get_kb_service


def render_ocr_tab(session: SessionManager):
    """渲染 OCR 对比标签页（PDF vs Markdown 分页）"""
    st.header("OCR 对比（分页）")
    
    if not session.current_kb_id or not session.current_doc_id:
        st.info("暂无选中的文档，请先在侧边栏选择文档")
        return
    
    kb_service = get_kb_service()
    
    # 加载文档数据
    pdf_bytes = kb_service.get_document_content(session.current_kb_id, session.current_doc_id)
    pages = kb_service.load_doc_pages(session.current_kb_id, session.current_doc_id)
    
    if not pdf_bytes or not pages:
        st.info("暂无数据，请先点击\"解析\"按钮")
        return
    
    # 页码选择器
    total_pages = len(pages)
    col_left, col_center, col_right = st.columns([1, 3, 1])
    with col_center:
        selected_page = st.selectbox(
            "选择页码",
            range(1, total_pages + 1),
            index=session.current_page_num - 1,
            format_func=lambda p: f"第 {p} 页",
            key="page_selector",
        )
        if selected_page != session.current_page_num:
            session.current_page_num = selected_page
            st.rerun()
    
    st.divider()
    
    # 左右对比：PDF + Markdown
    col_pdf, col_md = st.columns(2)
    
    with col_pdf:
        st.subheader(f"PDF 预览（第 {session.current_page_num} 页）")
        try:
            import pymupdf
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            page_idx = session.current_page_num - 1
            
            # 提取单页
            single_page_doc = pymupdf.Document()
            single_page_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
            single_page_bytes = single_page_doc.tobytes()
            
            doc.close()
            single_page_doc.close()
            
            render_pdf_viewer(single_page_bytes, height=720)
        except Exception as e:
            st.error(f"PDF 单页提取失败: {e}")
            # Fallback: 显示完整 PDF
            render_pdf_viewer(pdf_bytes, height=720)
    
    with col_md:
        st.subheader(f"Markdown（第 {session.current_page_num} 页）")
        current_md = pages[session.current_page_num - 1]
        display_md = current_md[:10000] if len(current_md) > 10000 else current_md
        st.markdown(display_md)
        if len(current_md) > 10000:
            st.caption("*(内容过长，仅显示前 10000 字符)*")
