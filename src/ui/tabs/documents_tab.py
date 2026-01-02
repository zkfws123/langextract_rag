"""文档管理标签页（参考 RAGFlow 的文件列表）- 每个文档独立工作流===已经作废 这个代码没用了"""
import os
import tempfile
import streamlit as st
from src.ui.session import SessionManager
from src.knowledge_base import KnowledgeBaseService, DocumentStatus
from src.parsers.mineru_parser import MinerUParser
from src.parsers.pipeline import KnowledgeExtractionPipeline
from src.graph.in_memory_store import InMemoryGraphStore
from src.retrieval.vector.chroma_store import ChromaVectorStore


def render_documents_tab(session: SessionManager, kb_service: KnowledgeBaseService):
    """渲染文档管理标签页 - 每个文档有独立的工作流按钮（左右布局）"""
    st.header("📄 文档管理")
    
    if not session.current_kb_id:
        st.info("💡 请先在左侧选择知识库")
        return
    
    kb = kb_service.get_kb(session.current_kb_id)
    if not kb:
        st.error("知识库不存在")
        return
    
    st.caption(f"知识库: **{kb.name}**")
    
    # 刷新文档列表
    docs = kb_service.list_documents(session.current_kb_id)
    
    if not docs:
        st.info("💡 暂无文档，请在左侧上传 PDF")
        return
    
    # 显示文档总数
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📚 文档总数", len(docs))
    with col2:
        completed = sum(1 for d in docs if d.status == DocumentStatus.COMPLETED)
        st.metric("✅ 已完成", completed)
    with col3:
        processing = sum(1 for d in docs if d.status == DocumentStatus.PROCESSING)
        st.metric("🔄 处理中", processing)
    
    st.divider()
    
    # 文档列表 - 每个文档展开项，左边信息右边4个按钮横排
    for doc in docs:
        with st.expander(f"📄 {doc.filename}", expanded=(doc.id == session.current_doc_id)):
            col_info, col_actions = st.columns([1, 2])
            
            # 左侧：文档信息
            with col_info:
                st.caption(f"📅 {doc.created_at.strftime('%Y-%m-%d %H:%M')}")
                status_map = {
                    DocumentStatus.PENDING: "⏳ 待处理",
                    DocumentStatus.PROCESSING: "🔄 处理中",
                    DocumentStatus.COMPLETED: "✅ 已完成",
                    DocumentStatus.ERROR: "❌ 出错"
                }
                st.caption(f"🟢 {status_map.get(doc.status, '❓')}")
                st.caption(f"📊 {doc.chunk_count}块 | {doc.entity_count}实体 | {doc.relation_count}关系")
            
            # 右侧：5个按钮横排（解析 | 提取 | 入库 | 清除 | 删除）
            with col_actions:
                c1, c2, c3, c4, c5 = st.columns(5)
                
                # 按钮1: 解析
                parse_done = doc.chunk_count > 0
                with c1:
                    if st.button("✅解析" if parse_done else "🚀解析", key=f"p_{doc.id}", 
                               disabled=parse_done, use_container_width=True):
                        with st.spinner("解析中..."):
                            try:
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
                                
                                st.success(f"✅ {len(pages)}页")
                                st.rerun()
                            except Exception as e:
                                st.error(f"失败: {e}")
                
                # 按钮2: 提取
                extract_done = doc.entity_count > 0
                with c2:
                    if st.button("✅提取" if extract_done else "🔍提取", key=f"e_{doc.id}",
                               disabled=(not parse_done) or extract_done, use_container_width=True):
                        with st.spinner("提取中..."):
                            try:
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
                                
                                st.success(f"✅ {len(extractions)}实体")
                                st.rerun()
                            except Exception as e:
                                st.error(f"失败: {e}")
                
                # 按钮3: 入库
                index_done = doc.status == DocumentStatus.COMPLETED
                with c3:
                    if st.button("✅入库" if index_done else "💾入库", key=f"i_{doc.id}",
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
                                
                                st.success("✅完成")
                                st.rerun()
                            except Exception as e:
                                st.error(f"失败: {e}")
                
                # 按钮4: 清除输出（重置文档处理状态）
                with c4:
                    if st.button("🧹清除", key=f"c_{doc.id}", use_container_width=True):
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
                            
                            st.success("已清除输出")
                            st.rerun()
                        except Exception as e:
                            st.error(f"清除失败: {e}")
                
                # 按钮5: 删除
                with c5:
                    if st.button("🗑️删除", key=f"d_{doc.id}", use_container_width=True):
                        kb_service.delete_document(session.current_kb_id, doc.id)
                        st.success("已删除")
                        st.rerun()
