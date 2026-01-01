"""文档处理工作流组件"""
import os
import tempfile
import streamlit as st
from src.ui.session import SessionManager
from src.knowledge_base import KnowledgeBaseService, DocumentStatus
from src.parsers.mineru_parser import MinerUParser
from src.parsers.local_pdf_parser import LocalPDFParser, PYMUPDF_AVAILABLE
from src.parsers.pipeline import KnowledgeExtractionPipeline
from src.agents import build_agent
from src.graph.in_memory_store import InMemoryGraphStore
from src.retrieval.vector.chroma_store import ChromaVectorStore


def render_doc_workflow(session: SessionManager, kb_service: KnowledgeBaseService):
    """渲染文档处理工作流侧边栏"""
    
    if not session.current_kb_id:
        st.info("请先选择知识库")
        return
    
    st.divider()
    st.subheader("📄 上传文档")
    
    # 文档上传
    uploaded_file = st.file_uploader(
        "上传 PDF 文档",
        type=["pdf"],
        help="支持中英文 PDF，建议文件大小 < 20MB",
        key="pdf_uploader"
    )
    
    if uploaded_file:
        pdf_bytes = uploaded_file.getvalue()
        
        # 检查是否是新文档
        if uploaded_file.name != session.uploaded_filename or pdf_bytes != session.pdf_bytes:
            session.pdf_bytes = pdf_bytes
            session.uploaded_filename = uploaded_file.name
            
            # 创建文档记录
            try:
                doc = kb_service.add_document(session.current_kb_id, uploaded_file.name, pdf_bytes)
                session.current_doc_id = doc.id
                session.doc_list_cache = kb_service.list_documents(session.current_kb_id)
                st.success(f"✅ 已添加文档: {uploaded_file.name}")
                # 立即刷新页面以更新文档列表
                st.rerun()
            except Exception as e:
                st.error(f"添加文档失败: {e}")
        
        st.info(f"当前文档: {uploaded_file.name}")
    
    if not session.current_doc_id:
        st.info("请先上传文档")
        return
    
    # 获取当前文档状态
    doc = kb_service.get_document(session.current_kb_id, session.current_doc_id)
    if not doc:
        st.error("文档记录丢失")
        return
    
    st.divider()
    st.subheader("⚙️ 工作流")
    
    # 解析方式选择
    parser_options = ["MinerU API (推荐)"]
    if PYMUPDF_AVAILABLE:
        parser_options.append("本地 PyMuPDF (备选)")
    parser_choice = st.radio("解析方式", parser_options, index=0, key="parser_choice")
    
    # 阶段1：解析 PDF
    parse_done = bool(session.markdown_content)
    parse_btn_label = "✅ 已解析" if parse_done else "🚀 解析 PDF"
    
    if st.button(parse_btn_label, disabled=parse_done or not session.pdf_bytes, use_container_width=True, key="parse_btn"):
        st.info(f"📄 开始解析: {doc.filename}")
        with st.spinner("正在解析 PDF..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(session.pdf_bytes)
                    tmp_path = tmp.name
                
                if "MinerU" in parser_choice:
                    parser = MinerUParser()
                    pages, offsets, zip_bytes, full_md = parser.parse_pdf_to_pages(tmp_path)
                else:
                    parser = LocalPDFParser()
                    full_md = parser.parse_pdf(tmp_path)
                    pages = [full_md]
                    offsets = [0]
                
                session.markdown_pages = pages
                session.page_offsets = offsets
                session.markdown_content = full_md
                session.current_page_num = 1
                
                # 保存到知识库
                kb_service.save_doc_markdown(session.current_kb_id, session.current_doc_id, full_md, pages)
                
                # 更新文档状态
                doc.status = DocumentStatus.PENDING
                doc.chunk_count = len(pages)
                kb_service.update_document(doc)
                
                st.success(f"✅ 解析完成: 共 {len(pages)} 页，{len(full_md):,} 字符")
                st.rerun()
            except Exception as e:
                st.error(f"解析失败: {e}")
                import traceback
                st.code(traceback.format_exc())
            finally:
                os.unlink(tmp_path)
    
    # 阶段2：提取知识
    extract_done = len(session.extractions) > 0
    extract_btn_label = "✅ 已提取" if extract_done else "🔍 提取知识"
    extract_disabled = not session.markdown_content or extract_done
    
    if st.button(extract_btn_label, disabled=extract_disabled, use_container_width=True, key="extract_btn"):
        st.info(f"🎯 开始提取知识...")
        with st.spinner("正在提取知识..."):
            try:
                # 获取自定义配置
                custom_prompt = session.extraction_prompt or None
                custom_examples = None
                
                if session.extraction_examples_parsed:
                    import langextract as lx
                    examples_data = session.extraction_examples_parsed
                    custom_examples = []
                    for ex_data in examples_data:
                        extractions_list = [
                            lx.data.Extraction(
                                extraction_class=ext["extraction_class"],
                                extraction_text=ext["extraction_text"],
                                attributes=ext.get("attributes", {})
                            )
                            for ext in ex_data["extractions"]
                        ]
                        custom_examples.append(
                            lx.data.ExampleData(
                                text=ex_data["text"],
                                extractions=extractions_list
                            )
                        )
                
                pipeline = KnowledgeExtractionPipeline(
                    doc_id=session.current_doc_id,
                    doc_title=doc.filename,
                    enable_relation_extraction=True,
                    custom_prompt=custom_prompt,
                    custom_examples=custom_examples
                )
                extractions, stage2_relations = pipeline.extract(session.markdown_content)
                session.extractions = extractions
                
                # 保存提取结果
                kb_service.save_doc_extractions(
                    session.current_kb_id,
                    session.current_doc_id,
                    [e.to_dict() for e in extractions]
                )
                
                # 更新文档状态
                doc.status = DocumentStatus.PROCESSING
                doc.entity_count = len(extractions)
                doc.relation_count = len(stage2_relations) if stage2_relations else 0
                kb_service.update_document(doc)
                
                st.success(f"✅ 知识提取完成: 共 {len(extractions)} 条知识点")
                st.rerun()
            except Exception as e:
                st.error(f"提取失败: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    # 阶段3：入库（增量合并）
    index_done = doc.status == DocumentStatus.COMPLETED
    index_btn_label = "✅ 已入库" if index_done else "💾 入库（增量）"
    index_disabled = not session.extractions or index_done
    
    if st.button(index_btn_label, disabled=index_disabled, use_container_width=True, key="index_btn"):
        st.info(f"📊 开始入库...")
        with st.spinner("正在入库并合并图谱..."):
            try:
                # 获取向量库collection
                collection_name = kb_service.get_collection_name(session.current_kb_id)
                if not session.vector_store:
                    session.vector_store = ChromaVectorStore(collection_name=collection_name)
                
                # 向量化
                st.info("⏳ 正在向量化知识点...")
                session.vector_store.index_extractions(session.extractions)
                
                # 构建临时图谱
                st.info("⏳ 正在提取关系...")
                from src.parsers.relation_extractor import RelationExtractor
                relation_extractor = RelationExtractor()
                stage2_relations = relation_extractor.extract_relations(
                    session.extractions,
                    session.markdown_content
                )
                
                temp_graph_store = InMemoryGraphStore()
                temp_graph_store.build_from_extractions(session.extractions, stage2_relations)
                
                # 增量合并到知识库图谱
                st.info("⏳ 正在合并到知识库...")
                merged_graph = kb_service.merge_graph(session.current_kb_id, temp_graph_store.knowledge_graph)
                
                # 更新 session 中的图谱
                session.graph_store = InMemoryGraphStore(merged_graph)
                
                # 更新文档状态
                doc.status = DocumentStatus.COMPLETED
                kb_service.update_document(doc)
                
                # 触发 Agent 重建
                session.agent_built = False
                
                st.success(f"✅ 入库完成！图谱已合并")
                st.info(f"🕸️ 当前知识库: {len(merged_graph.get('entities', {}))} 个实体, {len(merged_graph.get('relations', []))} 条关系")
                st.rerun()
            except Exception as e:
                st.error(f"入库失败: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    # 阶段4：构建 Agent
    agent_btn_label = "✅ Agent 已就绪" if session.agent_built else "🧠 构建 Agent"
    agent_disabled = not index_done or session.agent_built
    
    if st.button(agent_btn_label, disabled=agent_disabled, use_container_width=True, key="agent_btn"):
        st.info("🔧 正在初始化 Agent...")
        with st.spinner("正在构建 Agent..."):
            try:
                # 确保向量库和图谱已加载
                if not session.vector_store:
                    collection_name = kb_service.get_collection_name(session.current_kb_id)
                    session.vector_store = ChromaVectorStore(collection_name=collection_name)
                
                if not session.graph_store or not session.graph_store.knowledge_graph.get("entities"):
                    graph_data = kb_service.get_graph(session.current_kb_id)
                    session.graph_store = InMemoryGraphStore(graph_data)
                
                build_agent(session.vector_store, session.graph_store)
                session.agent_built = True
                st.success("✅ Agent 构建完成，可以开始问答")
                st.rerun()
            except Exception as e:
                st.error(f"构建失败: {e}")
                import traceback
                st.code(traceback.format_exc())
