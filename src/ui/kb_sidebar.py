"""知识库管理侧边栏"""
import streamlit as st
from src.ui.session import SessionManager
from src.knowledge_base import get_kb_service, KBStatus
from src.graph.in_memory_store import InMemoryGraphStore
from src.retrieval.vector.chroma_store import ChromaVectorStore


def render_kb_sidebar(session: SessionManager):
    """渲染知识库管理侧边栏"""
    kb_service = get_kb_service()
    
    st.header("知识库管理")
    
    # 刷新知识库列表
    kb_list = kb_service.list_kbs()
    session.kb_list_cache = kb_list
    
    if not kb_list:
        st.info("暂无知识库，请创建新知识库")
    else:
        # 知识库选择器
        kb_options = {f"{kb.name} ({kb.id})": kb.id for kb in kb_list}
        kb_options_list = ["--请选择--"] + list(kb_options.keys())
        
        # 确定当前选中项
        current_idx = 0
        if session.current_kb_id:
            for i, opt in enumerate(kb_options_list):
                if opt in kb_options and kb_options[opt] == session.current_kb_id:
                    current_idx = i
                    break
        
        col_select, col_del = st.columns([4, 1])
        
        with col_select:
            selected_label = st.selectbox(
                "选择知识库",
                kb_options_list,
                index=current_idx,
                key="kb_selector",
                label_visibility="collapsed"
            )
        
        with col_del:
            if st.button("🗑️", key="delete_kb", help="删除选中的知识库", disabled=(selected_label == "--请选择--")):
                if selected_label != "--请选择--":
                    kb_id = kb_options[selected_label]
                    try:
                        kb_service.delete_kb(kb_id)
                        if kb_id == session.current_kb_id:
                            session.switch_kb("")
                        st.success(f"已删除知识库: {selected_label}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {e}")
        
        # 处理知识库切换
        if selected_label != "--请选择--":
            selected_kb_id = kb_options[selected_label]
            if selected_kb_id != session.current_kb_id:
                # 切换知识库
                session.switch_kb(selected_kb_id)
                
                # 加载知识库的图谱和向量库
                try:
                    # 加载图谱
                    graph_data = kb_service.get_graph(selected_kb_id)
                    session.graph_store = InMemoryGraphStore(graph_data)
                    
                    # 加载向量库
                    kb = kb_service.get_kb(selected_kb_id)
                    if kb and kb.status == KBStatus.READY:
                        collection_name = kb_service.get_collection_name(selected_kb_id)
                        session.vector_store = ChromaVectorStore(collection_name=collection_name)
                    else:
                        session.vector_store = None
                    
                    # 加载文档列表
                    session.doc_list_cache = kb_service.list_documents(selected_kb_id)
                    
                    st.success(f"已切换到: {selected_label}")
                    st.rerun()
                except Exception as e:
                    st.error(f"切换失败: {e}")
    
    st.divider()
    
    # 创建新知识库
    with st.expander("➕ 创建新知识库", expanded=False):
        kb_name = st.text_input("知识库名称", key="new_kb_name")
        kb_desc = st.text_area("描述（可选）", key="new_kb_desc", height=80)
        
        if st.button("创建", use_container_width=True, key="create_kb_btn"):
            if not kb_name:
                st.error("请输入知识库名称")
            else:
                try:
                    new_kb = kb_service.create_kb(kb_name, kb_desc)
                    st.success(f"✅ 已创建知识库: {kb_name}")
                    session.switch_kb(new_kb.id)
                    st.rerun()
                except Exception as e:
                    st.error(f"创建失败: {e}")
    
    st.divider()
    
    # 显示当前知识库信息
    if session.current_kb_id:
        kb = kb_service.get_kb(session.current_kb_id)
        if kb:
            st.subheader(f"当前: {kb.name}")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("文档数", kb.document_count)
                st.metric("实体数", kb.total_entities)
            with col2:
                st.metric("关系数", kb.total_relations)
                st.metric("状态", kb.status.value)
            
            if kb.config.description:
                st.caption(kb.config.description)
            
            # 显示文档列表（参考 RAGFlow）
            st.divider()
            col_title, col_refresh = st.columns([4, 1])
            with col_title:
                st.subheader("文档列表")
            with col_refresh:
                if st.button("🔄", key="refresh_docs", help="刷新文档列表"):
                    session.doc_list_cache = kb_service.list_documents(session.current_kb_id)
                    st.rerun()
            
            # 刷新文档列表
            docs = kb_service.list_documents(session.current_kb_id)
            session.doc_list_cache = docs
            
            if not docs:
                st.info("暂无文档，请上传 PDF")
            else:
                st.caption(f"共 {len(docs)} 个文档")
                
                # RAGFlow 样式：每个文档一行，显示文档名和5个按钮
                for idx, doc in enumerate(docs):
                    from src.knowledge_base import DocumentStatus
                    import os
                    import tempfile
                    
                    status_text = {
                        "pending": "待处理",
                        "processing": "处理中",
                        "completed": "已完成",
                        "error": "出错"
                    }.get(doc.status.value, doc.status.value)
                    
                    # 展开项包含文档信息和按钮
                    is_current = (doc.id == session.current_doc_id)
                    with st.expander(f"{status_text} | {doc.filename} ({doc.chunk_count}块)", expanded=is_current):
                        # 按钮状态判断
                        parse_done = doc.chunk_count > 0
                        extract_done = doc.entity_count > 0
                        index_done = doc.status == DocumentStatus.COMPLETED
                        
                        # 5个按钮横向排列
                        c1, c2, c3, c4, c5 = st.columns(5)
                        
                        # 按钮1: 解析
                        with c1:
                            if st.button("完成" if parse_done else "解析", key=f"sidebar_p_{doc.id}", 
                                       disabled=parse_done, use_container_width=True):
                                with st.spinner("解析中..."):
                                    try:
                                        from src.parsers.mineru_parser import MinerUParser
                                        pdf_bytes = kb_service.get_document_content(session.current_kb_id, doc.id)
                                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                            tmp.write(pdf_bytes)
                                            tmp_path = tmp.name
                                        
                                        parser = MinerUParser()
                                        pages, offsets, zip_bytes, full_md = parser.parse_pdf_to_pages(tmp_path)
                                        kb_service.save_doc_markdown(session.current_kb_id, doc.id, full_md, pages)
                                        
                                        doc.chunk_count = len(pages)
                                        kb_service.update_document(doc)
                                        os.unlink(tmp_path)
                                        
                                        # 更新session状态
                                        session.current_doc_id = doc.id
                                        session.uploaded_filename = doc.filename
                                        session.markdown_content = full_md
                                        
                                        st.success(f"解析完成: {len(pages)}页")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"失败: {e}")
                        
                        # 按钮2: 提取
                        with c2:
                            if st.button("完成" if extract_done else "提取", key=f"sidebar_e_{doc.id}",
                                       disabled=(not parse_done) or extract_done, use_container_width=True):
                                with st.spinner("提取中..."):
                                    try:
                                        from src.parsers.pipeline import KnowledgeExtractionPipeline
                                        markdown = kb_service.load_doc_markdown(session.current_kb_id, doc.id)
                                        pipeline = KnowledgeExtractionPipeline(
                                            doc_id=doc.id,
                                            doc_title=doc.filename,
                                            enable_relation_extraction=True,
                                            custom_prompt=session.extraction_prompt
                                        )
                                        extractions, stage2_relations = pipeline.extract(markdown)
                                        
                                        kb_service.save_doc_extractions(
                                            session.current_kb_id, doc.id,
                                            [e.to_dict() for e in extractions]
                                        )
                                        
                                        doc.status = DocumentStatus.PROCESSING
                                        doc.entity_count = len(extractions)
                                        doc.relation_count = len(stage2_relations) if stage2_relations else 0
                                        kb_service.update_document(doc)
                                        
                                        # 更新session状态
                                        session.current_doc_id = doc.id
                                        session.uploaded_filename = doc.filename
                                        session.extractions = extractions
                                        
                                        st.success(f"提取完成: {len(extractions)}实体")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"失败: {e}")
                        
                        # 按钮3: 入库
                        with c3:
                            if st.button("完成" if index_done else "入库", key=f"sidebar_i_{doc.id}",
                                       disabled=(not extract_done) or index_done, use_container_width=True):
                                with st.spinner("入库中..."):
                                    try:
                                        from src.graph.models import KnowledgeExtraction
                                        from src.parsers.relation_extractor import RelationExtractor
                                        
                                        extractions_data = kb_service.load_doc_extractions(session.current_kb_id, doc.id)
                                        extractions = [KnowledgeExtraction(**e) for e in extractions_data]
                                        
                                        # 向量化
                                        collection_name = kb_service.get_collection_name(session.current_kb_id)
                                        vector_store = ChromaVectorStore(collection_name=collection_name)
                                        vector_store.index_extractions(extractions)
                                        
                                        # 提取关系并合并图谱
                                        markdown = kb_service.load_doc_markdown(session.current_kb_id, doc.id)
                                        relation_extractor = RelationExtractor()
                                        stage2_relations = relation_extractor.extract_relations(extractions, markdown)
                                        
                                        temp_graph = InMemoryGraphStore()
                                        temp_graph.build_from_extractions(extractions, stage2_relations)
                                        kb_service.merge_graph(session.current_kb_id, temp_graph.knowledge_graph)
                                        
                                        doc.status = DocumentStatus.COMPLETED
                                        kb_service.update_document(doc)
                                        
                                        # 更新session状态
                                        session.current_doc_id = doc.id
                                        session.uploaded_filename = doc.filename
                                        session.graph_store = InMemoryGraphStore(kb_service.get_graph(session.current_kb_id))
                                        session.vector_store = vector_store
                                        
                                        st.success("入库完成")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"失败: {e}")
                        
                        # 按钮4: 清除输出
                        with c4:
                            if st.button("清除", key=f"sidebar_c_{doc.id}", use_container_width=True):
                                try:
                                    # 删除文档相关的所有输出
                                    doc_dir = kb_service._doc_dir(session.current_kb_id, doc.id)
                                    for file in ["content.md", "pages.json", "extractions.json"]:
                                        file_path = doc_dir / file
                                        if file_path.exists():
                                            file_path.unlink()
                                    
                                    # 重置文档状态
                                    doc.status = DocumentStatus.PENDING
                                    doc.chunk_count = 0
                                    doc.entity_count = 0
                                    doc.relation_count = 0
                                    kb_service.update_document(doc)
                                    
                                    st.success("已清除")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"清除失败: {e}")
                        
                        # 按钮5: 删除文档
                        with c5:
                            if st.button("删除", key=f"sidebar_d_{doc.id}", use_container_width=True):
                                kb_service.delete_document(session.current_kb_id, doc.id)
                                if doc.id == session.current_doc_id:
                                    session.current_doc_id = ""
                                st.success("已删除")
                                st.rerun()
    
    return kb_service
