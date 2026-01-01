"""
GraphRAG Streamlit UI - PDF 上传 + 知识提取 + Agent 问答 + 溯源可视化
"""

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# 添加项目根目录到 path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=True)

from src.parsers.mineru_parser import MinerUParser
from src.parsers.local_pdf_parser import LocalPDFParser, PYMUPDF_AVAILABLE
from src.parsers.pipeline import KnowledgeExtractionPipeline
from src.retrieval.vector.chroma_store import ChromaVectorStore
from src.graph.in_memory_store import InMemoryGraphStore
from src.graph.models import KnowledgeExtraction
from src.agents import build_agent, agent_query
from src.ui.components import (
    render_pdf_viewer,
    render_markdown_preview,
    render_insights,
    clear_session_state,
)
from src.utils.run_cache import (
    DocumentRunCache,
    RunState,
    doc_hash,
    list_cached_runs,
)
from src.configs import ConfigType, get_config

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
# Session State 初始化（支持多文档运行）
# ============================================================================
if "current_doc_hash" not in st.session_state:
    st.session_state.current_doc_hash = ""
if "run_state" not in st.session_state:
    st.session_state.run_state = RunState(doc_hash="")
if "run_cache" not in st.session_state:
    st.session_state.run_cache = None

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None
if "graph_store" not in st.session_state:
    st.session_state.graph_store = InMemoryGraphStore()
if "agent_built" not in st.session_state:
    st.session_state.agent_built = False
if "markdown_content" not in st.session_state:
    st.session_state.markdown_content = ""
if "markdown_pages" not in st.session_state:
    st.session_state.markdown_pages = []
if "page_offsets" not in st.session_state:
    st.session_state.page_offsets = []
if "extractions" not in st.session_state:
    st.session_state.extractions = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = b""
if "uploaded_name" not in st.session_state:
    st.session_state.uploaded_name = ""
if "current_page_num" not in st.session_state:
    st.session_state.current_page_num = 1


# ============================================================================
# 侧边栏: 文档管理（多文档运行支持）
# ============================================================================
with st.sidebar:
    st.header("📄 文档管理")

    # --- 1) 已有运行列表 ---
    cached_runs = list_cached_runs()
    if cached_runs:
        st.subheader("已缓存运行")
        
        col_select, col_delete = st.columns([4, 1])
        
        with col_select:
            run_options = {f"{r.doc_name} ({r.doc_hash})": r.doc_hash for r in cached_runs}
            selected_label = st.selectbox("选择已有运行", ["--新建--"] + list(run_options.keys()), label_visibility="collapsed")
        
        with col_delete:
            if st.button("🗑️", key="delete_cached_run", help="删除选中的缓存"):
                if selected_label != "--新建--":
                    selected_hash = run_options[selected_label]
                    try:
                        import shutil
                        cache_to_delete = DocumentRunCache(selected_hash)
                        run_dir = cache_to_delete._root
                        if run_dir.exists():
                            shutil.rmtree(run_dir)
                        
                        # If deleting current doc, reset session
                        if selected_hash == st.session_state.current_doc_hash:
                            clear_session_state([
                                "markdown_content", "markdown_pages", "page_offsets",
                                "extractions", "chat_history", "pdf_bytes", "uploaded_name",
                                "current_page_num"
                            ])
                            st.session_state.current_doc_hash = ""
                            st.session_state.run_state = RunState(doc_hash="")
                            st.session_state.run_cache = None
                        
                        st.success(f"已删除缓存: {selected_label}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {e}")
        
        if selected_label != "--新建--":
            selected_hash = run_options[selected_label]
            if selected_hash != st.session_state.current_doc_hash:
                # 切换到已有运行：加载缓存
                st.session_state.current_doc_hash = selected_hash
                cache = DocumentRunCache(selected_hash)
                st.session_state.run_cache = cache
                st.session_state.run_state = cache.load_state()

                # 恢复 PDF
                pdf_bytes = cache.load_pdf()
                if pdf_bytes:
                    st.session_state.pdf_bytes = pdf_bytes
                    st.session_state.uploaded_name = st.session_state.run_state.doc_name

                # 恢复解析产物
                pages_data = cache.load_pages()
                if pages_data:
                    pages, offsets, full_md = pages_data
                    st.session_state.markdown_pages = pages
                    st.session_state.page_offsets = offsets
                    st.session_state.markdown_content = full_md
                    st.session_state.current_page_num = 1

                # 恢复抽取
                ext_data = cache.load_extractions()
                if ext_data:
                    from src.graph.models import KnowledgeExtraction as _KnowledgeExtraction
                    st.session_state.extractions = [
                        _KnowledgeExtraction(**e) for e in ext_data
                    ]

                # 恢复图
                graph_data = cache.load_graph()
                if graph_data:
                    st.session_state.graph_store = InMemoryGraphStore(graph_data)

                # 若图为空但已有抽取，自动重建图（适配紫微等非“实体/关系描述”类别）
                try:
                    kg_now = st.session_state.graph_store.knowledge_graph
                    graph_empty = not kg_now.get("entities") and not kg_now.get("relations")
                    if graph_empty and st.session_state.extractions:
                        st.session_state.graph_store = InMemoryGraphStore()
                        st.session_state.graph_store.build_from_extractions(st.session_state.extractions)
                        cache.save_graph(st.session_state.graph_store.knowledge_graph)
                except Exception:
                    pass

                # 恢复向量库（按 doc_hash 切换 collection）
                if st.session_state.run_state.stage_index_done:
                    st.session_state.vector_store = ChromaVectorStore(
                        collection_name=f"doc_{selected_hash}"
                    )
                    # 刷新/重载后内存 Agent 会丢失：需要重新 build
                    try:
                        build_agent(st.session_state.vector_store, st.session_state.graph_store)
                        st.session_state.agent_built = True
                    except Exception as e:
                        st.session_state.agent_built = False
                        st.error(f"Agent 恢复失败（可点击【🧠 构建 Agent】重试）: {e}")
                else:
                    st.session_state.vector_store = None
                    st.session_state.agent_built = False

                st.success(f"已加载运行: {st.session_state.run_state.doc_name}")
                st.rerun()

    st.divider()

    # --- 3) LLM 模型 ---
    with st.expander("🤖 LLM 模型", expanded=False):
        llm_options = ["ds", "gemini3flash", "gemini3pro", "sonetto5high", "sonetto_gemini3pro"]

        if "active_llm" not in st.session_state:
            # 默认：若环境里有 Gemini 配置则优先用 gemini3flash，否则用 ds
            has_gemini = bool(os.getenv("GEMINI_API_KEY")) and bool(os.getenv("GEMINI_BASE_URL"))
            st.session_state.active_llm = os.getenv("ACTIVE_LLM") or ("gemini3flash" if has_gemini else "ds")

        active_llm = st.selectbox(
            "LLM 模型",
            llm_options,
            index=llm_options.index(st.session_state.active_llm) if st.session_state.active_llm in llm_options else 0,
            key="llm_model_selector",
            label_visibility="collapsed",
        )

        st.caption(f"当前 ACTIVE_LLM: {st.session_state.active_llm}")

        if active_llm != st.session_state.active_llm:
            st.session_state.active_llm = active_llm
            os.environ["ACTIVE_LLM"] = active_llm
            # 切换模型后需要重新构建 Agent
            st.session_state.agent_built = False
            st.success(f"✅ 已切换 LLM: {active_llm}")
            st.rerun()

    # --- 2) 上传新文档 ---
    st.subheader("上传新文档")

    uploaded_file = st.file_uploader(
        "上传 PDF 文档",
        type=["pdf"],
        help="支持中英文 PDF，建议文件大小 < 20MB",
    )

    if uploaded_file:
        pdf_bytes = uploaded_file.getvalue()
        new_hash = doc_hash(pdf_bytes)

        # 若 hash 变化，重置当前运行
        if new_hash != st.session_state.current_doc_hash:
            st.session_state.current_doc_hash = new_hash
            cache = DocumentRunCache(new_hash)
            st.session_state.run_cache = cache
            # 检查是否已有解析缓存
            existing_state = cache.load_state()
            if existing_state.doc_name:
                st.session_state.run_state = existing_state
                st.info(f"检测到已解析：{existing_state.doc_name}")
            else:
                st.session_state.run_state = RunState(doc_hash=new_hash, doc_name=uploaded_file.name)
                cache.save_state(st.session_state.run_state)

            st.session_state.pdf_bytes = pdf_bytes
            st.session_state.uploaded_name = uploaded_file.name
            cache.save_pdf(pdf_bytes)

            # 尝试恢复缓存
            pages_data = cache.load_pages()
            if pages_data:
                pages, offsets, full_md = pages_data
                st.session_state.markdown_pages = pages
                st.session_state.page_offsets = offsets
                st.session_state.markdown_content = full_md
                st.session_state.current_page_num = 1

            ext_data = cache.load_extractions()
            if ext_data:
                from src.graph.models import KnowledgeExtraction as _KnowledgeExtraction
                st.session_state.extractions = [_KnowledgeExtraction(**e) for e in ext_data]

            graph_data = cache.load_graph()
            if graph_data:
                st.session_state.graph_store = InMemoryGraphStore(graph_data)
            # 若索引已完成，自动恢复向量库并重建内存 Agent（刷新页面后需要）
            if st.session_state.run_state.stage_index_done:
                try:
                    st.session_state.vector_store = ChromaVectorStore(
                        collection_name=f"doc_{st.session_state.current_doc_hash}"
                    )
                    build_agent(st.session_state.vector_store, st.session_state.graph_store)
                    st.session_state.agent_built = True
                except Exception as e:
                    st.session_state.vector_store = None
                    st.session_state.agent_built = False
                    st.error(f"Agent 恢复失败（可点击【🧠 构建 Agent】重试）: {e}")

            # 若图为空但已有抽取，自动重建图（适配紫微等非“实体/关系描述”类别）
            try:
                kg_now = st.session_state.graph_store.knowledge_graph
                graph_empty = not kg_now.get("entities") and not kg_now.get("relations")
                if graph_empty and st.session_state.extractions:
                    st.session_state.graph_store = InMemoryGraphStore()
                    st.session_state.graph_store.build_from_extractions(st.session_state.extractions)
                    cache.save_graph(st.session_state.graph_store.knowledge_graph)
            except Exception:
                pass

            if st.session_state.run_state.stage_index_done:
                st.session_state.vector_store = ChromaVectorStore(collection_name=f"doc_{new_hash}")
                st.session_state.agent_built = True
            else:
                st.session_state.vector_store = None
                st.session_state.agent_built = False

            st.rerun()

        st.success(f"已选择: {uploaded_file.name}")

    st.divider()

    # --- 3) 提取配置 ---
    with st.expander("⚙️ 知识提取配置", expanded=False):
        st.markdown("**📚 文档类型选择**")
        
        # 文档类型选择（默认紫微斗数）
        doc_type_options = {
            ConfigType.get_display_name(ConfigType.ZIWEI_DOUSHU): ConfigType.ZIWEI_DOUSHU,
            ConfigType.get_display_name(ConfigType.GENERAL): ConfigType.GENERAL,
        }
        
        if "selected_doc_type" not in st.session_state:
            st.session_state.selected_doc_type = ConfigType.ZIWEI_DOUSHU
        
        selected_type_name = st.selectbox(
            "文档类型",
            list(doc_type_options.keys()),
            index=0 if st.session_state.selected_doc_type == ConfigType.ZIWEI_DOUSHU else 1,
            key="doc_type_selector",
            label_visibility="collapsed"
        )
        
        # 检测类型变化，自动加载配置
        new_type = doc_type_options[selected_type_name]
        if new_type != st.session_state.selected_doc_type:
            st.session_state.selected_doc_type = new_type
            # 加载对应的默认配置
            default_prompt, default_examples = get_config(new_type)
            st.session_state.extraction_prompt = default_prompt
            
            # 转换 examples 为 JSON 格式和字典格式
            import json
            examples_json = []
            for ex in default_examples:
                examples_json.append({
                    "text": ex.text,
                    "extractions": [
                        {
                            "extraction_class": ext.extraction_class,
                            "extraction_text": ext.extraction_text,
                            "attributes": ext.attributes
                        }
                        for ext in ex.extractions
                    ]
                })
            st.session_state.extraction_examples_json = json.dumps(examples_json, ensure_ascii=False, indent=2)
            st.session_state.extraction_examples_parsed = examples_json  # 存储字典格式，不是对象
            st.success(f"✅ 已切换到 {selected_type_name} 配置")
            st.rerun()
        
        st.divider()
        st.markdown("**自定义提取 Prompt**")
        
        # 如果没有设置过，使用当前类型的默认配置
        if "extraction_prompt" not in st.session_state:
            default_prompt, default_examples = get_config(st.session_state.selected_doc_type)
            st.session_state.extraction_prompt = default_prompt
            # 转换 examples 为 JSON 格式和字典格式
            import json
            examples_json = []
            for ex in default_examples:
                examples_json.append({
                    "text": ex.text,
                    "extractions": [
                        {
                            "extraction_class": ext.extraction_class,
                            "extraction_text": ext.extraction_text,
                            "attributes": ext.attributes
                        }
                        for ext in ex.extractions
                    ]
                })
            st.session_state.extraction_examples_json = json.dumps(examples_json, ensure_ascii=False, indent=2)
            st.session_state.extraction_examples_parsed = examples_json  # 存储字典格式，不是对象
        
        custom_prompt = st.text_area(
            "Extraction Prompt",
            value=st.session_state.extraction_prompt,
            height=200,
            help="描述要从文档中提取的知识类型和要求",
            label_visibility="collapsed"
        )
        
        if st.button("💾 保存 Prompt", use_container_width=True):
            st.session_state.extraction_prompt = custom_prompt
            st.success("✅ Prompt 已更新")
        
        st.divider()
        st.markdown("**Few-Shot Examples (JSON格式)**")
        st.caption("提供1-3个示例，教模型输出格式")
        
        custom_examples_json = st.text_area(
            "Examples JSON",
            value=st.session_state.extraction_examples_json,
            height=250,
            help="JSON数组格式，每个对象包含text和extractions字段",
            label_visibility="collapsed"
        )
        
        if st.button("💾 保存 Examples", use_container_width=True):
            try:
                import json
                examples_data = json.loads(custom_examples_json)
                st.session_state.extraction_examples_json = custom_examples_json
                st.session_state.extraction_examples_parsed = examples_data
                st.success(f"✅ Examples 已更新（{len(examples_data)}个）")
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON 格式错误: {e}")

    st.divider()

    # --- 4) 工作流按钮（按阶段拆分） ---
    st.subheader("工作流")

    # 解析方式选择
    parser_options = ["MinerU API (推荐)"]
    if PYMUPDF_AVAILABLE:
        parser_options.append("本地 PyMuPDF (备选)")
    parser_choice = st.radio("解析方式", parser_options, index=0)

    run_state = st.session_state.run_state
    cache = st.session_state.run_cache

    # 按钮A：🚀 解析 PDF
    parse_disabled = not st.session_state.pdf_bytes or run_state.stage_parse_done
    if st.button(
        "🚀 解析 PDF" if not run_state.stage_parse_done else "✅ 已解析",
        disabled=parse_disabled,
        use_container_width=True,
    ):
        st.info(f"📄 开始解析: {st.session_state.uploaded_name}")
        st.info(f"📦 文件大小: {len(st.session_state.pdf_bytes) / 1024:.1f} KB")
        
        with st.spinner("正在解析 PDF..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(st.session_state.pdf_bytes)
                tmp_path = tmp.name

            try:
                if "MinerU" in parser_choice:
                    parser = MinerUParser()
                    pages, offsets, zip_bytes, full_md = parser.parse_pdf_to_pages(tmp_path)
                    cache.save_zip(zip_bytes)
                else:
                    parser = LocalPDFParser()
                    full_md = parser.parse_pdf(tmp_path)
                    # fallback: no pages split
                    pages = [full_md]
                    offsets = [0]

                st.session_state.markdown_pages = pages
                st.session_state.page_offsets = offsets
                st.session_state.markdown_content = full_md
                st.session_state.current_page_num = 1

                cache.save_pages(pages, offsets)

                run_state.stage_parse_done = True
                cache.save_state(run_state)
                
                # 显示解析统计
                st.success(f"✅ 解析完成: 共 {len(pages)} 页")
                st.info(f"📝 提取文本: {len(full_md):,} 字符")
                st.rerun()

            except Exception as e:
                st.error(f"解析失败: {e}")
                import traceback

                st.code(traceback.format_exc())
            finally:
                os.unlink(tmp_path)

    # 按钮B：🔍 提取知识
    extract_disabled = not run_state.stage_parse_done or run_state.stage_extract_done
    if st.button(
        "🔍 提取知识" if not run_state.stage_extract_done else "✅ 已提取",
        disabled=extract_disabled,
        use_container_width=True,
    ):
        st.info(f"🎯 使用配置: {ConfigType.get_display_name(st.session_state.selected_doc_type)}")
        st.info(f"📊 待处理文本: {len(st.session_state.markdown_content):,} 字符")
        
        with st.spinner("正在提取知识..."):
            try:
                # 获取自定义配置
                custom_prompt = st.session_state.get("extraction_prompt", None)
                custom_examples = None
                
                if "extraction_examples_parsed" in st.session_state:
                    import langextract as lx
                    examples_data = st.session_state.extraction_examples_parsed
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
                    doc_id=st.session_state.current_doc_hash,
                    doc_title=st.session_state.uploaded_name,
                    enable_relation_extraction=True,
                    custom_prompt=custom_prompt,
                    custom_examples=custom_examples
                )
                extractions, stage2_relations = pipeline.extract(st.session_state.markdown_content)
                st.session_state.extractions = extractions

                # 基于抽取结果立即构建图谱（即使尚未“入库”也能可视化）
                st.info("⏳ 正在根据抽取结果构建知识图谱...")
                st.session_state.graph_store = InMemoryGraphStore()
                st.session_state.graph_store.build_from_extractions(extractions, stage2_relations)
                cache.save_graph(st.session_state.graph_store.knowledge_graph)

                # 持久化
                cache.save_extractions([e.to_dict() for e in extractions])

                run_state.stage_extract_done = True
                cache.save_state(run_state)
                
                # 分类统计
                class_counts = {}
                for ext in extractions:
                    cls = ext.extraction_class
                    class_counts[cls] = class_counts.get(cls, 0) + 1
                
                st.success(f"✅ 知识提取完成: 共 {len(extractions)} 条")
                st.info(f"📋 分类统计: {dict(class_counts)}")
                kg = st.session_state.graph_store.knowledge_graph
                st.info(f"🕸️ 图谱已生成: {len(kg.get('entities', {}))} 个节点, {len(kg.get('relations', []))} 条边")
                st.rerun()

            except Exception as e:
                st.error(f"提取失败: {e}")
                import traceback

                st.code(traceback.format_exc())

    # 按钮C：💾 入库+构图
    index_disabled = not run_state.stage_extract_done or run_state.stage_index_done
    if st.button(
        "💾 入库+构图" if not run_state.stage_index_done else "✅ 已入库",
        disabled=index_disabled,
        use_container_width=True,
    ):
        st.info(f"📊 准备入库: {len(st.session_state.extractions)} 条知识")
        
        with st.spinner("正在入库并构图..."):
            try:
                # 初始化或获取 vector_store
                if not st.session_state.vector_store:
                    st.session_state.vector_store = ChromaVectorStore(
                        collection_name=f"doc_{st.session_state.current_doc_hash}"
                    )
                    st.info("✓ 向量库初始化完成")

                st.info("⏳ 正在向量化知识点...")
                st.session_state.vector_store.index_extractions(st.session_state.extractions)
                st.info("✓ 向量化完成")
                
                st.info("⏳ 正在构建知识图谱（含关系）...")
                # 重新提取关系（确保图谱完整）
                from src.parsers.relation_extractor import RelationExtractor
                relation_extractor = RelationExtractor()
                stage2_relations = relation_extractor.extract_relations(
                    st.session_state.extractions,
                    st.session_state.markdown_content
                )
                
                # 避免重复构图造成节点/边累积
                st.session_state.graph_store = InMemoryGraphStore()
                st.session_state.graph_store.build_from_extractions(
                    st.session_state.extractions,
                    stage2_relations
                )

                # 持久化图
                cache.save_graph(st.session_state.graph_store.knowledge_graph)

                run_state.stage_index_done = True
                cache.save_state(run_state)
                
                # 显示图谱统计
                kg = st.session_state.graph_store.knowledge_graph
                entity_count = len(kg.get("entities", {}))
                relation_count = len(kg.get("relations", []))
                
                st.success("✅ 入库+构图完成")
                st.info(f"🕸️ 图谱统计: {entity_count} 个实体, {relation_count} 条关系")
                st.rerun()

            except Exception as e:
                st.error(f"入库失败: {e}")
                import traceback

                st.code(traceback.format_exc())

    # 按钮D：🧠 构建 Agent
    agent_disabled = not run_state.stage_index_done or st.session_state.agent_built
    if st.button(
        "🧠 构建 Agent" if not st.session_state.agent_built else "✅ Agent 已就绪",
        disabled=agent_disabled,
        use_container_width=True,
    ):
        st.info("🔧 正在初始化 Agent 工具...")
        
        with st.spinner("正在构建 Agent..."):
            try:
                st.info("⏳ 加载向量检索工具...")
                st.info("⏳ 加载图谱查询工具...")
                build_agent(st.session_state.vector_store, st.session_state.graph_store)
                st.session_state.agent_built = True
                st.success("✅ Agent 构建完成，可以开始问答")
                st.rerun()

            except Exception as e:
                st.error(f"构建失败: {e}")
                import traceback

                st.code(traceback.format_exc())

    
    st.divider()
    if st.button("🗑️ 清空本次解析", use_container_width=True):
        if st.session_state.run_cache:
            st.session_state.run_cache.clear()
        clear_session_state([
            "markdown_content",
            "markdown_pages",
            "page_offsets",
            "extractions",
            "chat_history",
            "pdf_bytes",
            "uploaded_name",
            "current_page_num",
        ])
        st.session_state.vector_store = None
        st.session_state.graph_store = InMemoryGraphStore()
        st.session_state.agent_built = False
        st.session_state.current_doc_hash = ""
        st.session_state.run_state = RunState(doc_hash="")
        st.session_state.run_cache = None
        st.success("已清空当前解析数据")
        st.rerun()
    
    st.divider()
    
    # 显示知识库状态
    st.subheader("📊 知识库状态")
    kg = st.session_state.graph_store.knowledge_graph
    col1, col2 = st.columns(2)
    with col1:
        st.metric("实体数", len(kg.get("entities", {})))
    with col2:
        st.metric("关系数", len(kg.get("relations", [])))
    
    if st.session_state.agent_built:
        st.success("Agent 已就绪 ✓")
    else:
        st.warning("请先上传文档")


# ============================================================================
# 兜底：自动从缓存加载/重建图谱（解决旧缓存 graph.json 为空导致前端图谱空）
# ============================================================================
def _ensure_graph_loaded_from_cache() -> None:
    doc_id = st.session_state.get("current_doc_hash") or ""
    if not doc_id:
        return

    try:
        cache = st.session_state.get("run_cache") or DocumentRunCache(doc_id)
    except Exception:
        return

    # 1) Ensure extractions in memory
    if not st.session_state.get("extractions"):
        ext_data = cache.load_extractions()
        if ext_data:
            from src.graph.models import KnowledgeExtraction as _KnowledgeExtraction
            st.session_state.extractions = [_KnowledgeExtraction(**e) for e in ext_data]

    # 2) Load graph.json if available
    try:
        kg_now = st.session_state.graph_store.knowledge_graph
    except Exception:
        kg_now = {"entities": {}, "relations": []}

    has_graph = bool(kg_now.get("entities")) or bool(kg_now.get("relations"))
    if not has_graph:
        graph_data = cache.load_graph()
        if graph_data:
            st.session_state.graph_store = InMemoryGraphStore(graph_data)
            kg_now = st.session_state.graph_store.knowledge_graph
            has_graph = bool(kg_now.get("entities")) or bool(kg_now.get("relations"))

    # 3) If still empty but we have extractions, rebuild and persist
    if (not has_graph) and st.session_state.get("extractions"):
        st.session_state.graph_store = InMemoryGraphStore()
        st.session_state.graph_store.build_from_extractions(st.session_state.extractions)
        cache.save_graph(st.session_state.graph_store.knowledge_graph)


_ensure_graph_loaded_from_cache()


# ============================================================================
# 主区域: 标签页
# ============================================================================
tab1, tab_ocr, tab2, tab3, tab4, tab_insights = st.tabs([
    "💬 问答",
    "🖼️ OCR 对比",
    "📜 解析预览",
    "🕸️ 知识图谱",
    "📋 提取结果",
    "🧭 抽取洞察",
])

# ----------------------------------------------------------------------------
# Tab 1: 问答
# ----------------------------------------------------------------------------
with tab1:
    st.header("GraphRAG 智能问答")

    # 兜底：刷新页面后内存 Agent 可能丢失，但缓存/索引已完成
    if (not st.session_state.agent_built) and st.session_state.run_state.stage_index_done:
        try:
            if not st.session_state.vector_store:
                st.session_state.vector_store = ChromaVectorStore(
                    collection_name=f"doc_{st.session_state.current_doc_hash}"
                )
            build_agent(st.session_state.vector_store, st.session_state.graph_store)
            st.session_state.agent_built = True
            st.success("✅ 已自动恢复 Agent，可直接问答")
        except Exception as e:
            st.session_state.agent_built = False
            st.error(f"Agent 自动恢复失败，请点击左侧【🧠 构建 Agent】: {e}")
    
    if not st.session_state.agent_built:
        st.info("👈 请先在左侧上传并解析文档")
    else:
        # 显示对话历史
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("evidence"):
                    with st.expander("📎 查看证据溯源"):
                        for ev in msg["evidence"]:
                            if ev.get("type") == "result":
                                st.code(ev.get("content", ""), language="text")
        
        # 输入框
        if prompt := st.chat_input("输入您的问题..."):
            # 显示用户消息
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Agent 回答
            with st.chat_message("assistant"):
                with st.spinner("思考中..."):
                    result = agent_query(prompt)
                    answer = result.get("answer", "无法回答")
                    evidence = result.get("evidence", [])
                
                st.markdown(answer)
                
                if evidence:
                    with st.expander("📎 查看证据溯源"):
                        for ev in evidence:
                            if ev.get("type") == "result":
                                st.code(ev.get("content", ""), language="text")
                
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "evidence": evidence
                })

# ----------------------------------------------------------------------------
# Tab OCR: PDF vs Markdown（分页对比）
# ----------------------------------------------------------------------------
with tab_ocr:
    st.header("🖼️ OCR 对比（分页）")

    if not st.session_state.pdf_bytes or not st.session_state.markdown_pages:
        st.info("暂无数据，请先上传并解析 PDF")
    else:
        # 页码选择器（居中放在上方）
        total_pages = len(st.session_state.markdown_pages)
        col_left, col_center, col_right = st.columns([1, 3, 1])
        with col_center:
            selected_page = st.selectbox(
                "选择页码",
                range(1, total_pages + 1),
                index=st.session_state.current_page_num - 1,
                format_func=lambda p: f"第 {p} 页",
                key="page_selector",
            )
            if selected_page != st.session_state.current_page_num:
                st.session_state.current_page_num = selected_page
                st.rerun()

        st.divider()

        # 左右对比：PDF（带页面跳转消息发送） + 当前页 Markdown
        col_pdf, col_md = st.columns(2)

        with col_pdf:
            st.subheader(f"PDF 预览（第 {st.session_state.current_page_num} 页）")
            
            # 提取当前选择页的单页PDF
            try:
                import pymupdf
                doc = pymupdf.open(stream=st.session_state.pdf_bytes, filetype="pdf")
                page_idx = st.session_state.current_page_num - 1  # Convert to 0-based
                
                # Create new document with only selected page
                single_page_doc = pymupdf.Document()
                single_page_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
                single_page_bytes = single_page_doc.tobytes()
                
                doc.close()
                single_page_doc.close()
                
                # Render single page
                render_pdf_viewer(single_page_bytes, height=720)
            except Exception as e:
                st.error(f"PDF 单页提取失败: {e}")
                # Fallback: show full PDF
                render_pdf_viewer(st.session_state.pdf_bytes, height=720)

        with col_md:
            st.subheader(f"Markdown（第 {st.session_state.current_page_num} 页）")
            current_md = st.session_state.markdown_pages[st.session_state.current_page_num - 1]
            st.markdown(current_md if len(current_md) < 10000 else current_md[:10000] + "\n\n*(内容过长，仅显示前 10000 字符)*")

# ----------------------------------------------------------------------------
# Tab 2: 解析预览
# ----------------------------------------------------------------------------
with tab2:
    st.header("📜 PDF 解析结果")
    
    if st.session_state.markdown_content:
        st.markdown(st.session_state.markdown_content[:10000])
        if len(st.session_state.markdown_content) > 10000:
            st.info(f"内容过长，仅显示前 10000 字符 (共 {len(st.session_state.markdown_content)} 字符)")
    else:
        st.info("暂无解析内容，请先上传 PDF")

# ----------------------------------------------------------------------------
# Tab 3: 知识图谱可视化
# ----------------------------------------------------------------------------
with tab3:
    st.header("🕸️ 知识图谱可视化")
    
    kg = st.session_state.graph_store.knowledge_graph
    entities = kg.get("entities", {})
    relations = kg.get("relations", [])
    
    # 显示当前状态
    if entities:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📍 实体节点", len(entities))
        with col2:
            st.metric("🔗 关系边", len(relations))
    
    if not entities:
        st.info("💡 暂无图谱数据")
        if not st.session_state.run_state.stage_extract_done:
            st.warning("👈 请先完成【🔍 提取知识】步骤")
        elif not st.session_state.run_state.stage_index_done:
            st.warning("👈 请先完成【💾 入库+构图】步骤")
    else:
        try:
            with st.spinner("🔄 正在加载图谱可视化..."):
                try:
                    from pyvis.network import Network
                    import networkx as nx
                except ImportError as ie:
                    st.error(f"❌ 缺少依赖库: {ie}")
                    st.code("pip install pyvis networkx")
                    st.stop()
            
            # 构建 networkx 图
            G = nx.DiGraph()
            
            # 添加实体节点
            for name, data in entities.items():
                entity_type = data.get("type", "未知")
                color = {
                    "实体": "#4ECDC4",
                    "数据指标": "#FF6B6B",
                    "关系描述": "#45B7D1",
                }.get(entity_type, "#95A5A6")
                G.add_node(name, title=f"{entity_type}\n{data.get('attributes', {})}", color=color)
            
            # 添加关系边
            for rel in relations:
                subj = rel.get("subject")
                obj = rel.get("object")
                rel_type = rel.get("relation") or rel.get("type", "关联")
                if subj and obj:
                    if subj not in G:
                        G.add_node(subj, color="#95A5A6")
                    if obj not in G:
                        G.add_node(obj, color="#95A5A6")
                    G.add_edge(subj, obj, title=rel_type, label=rel_type)
            
            # 使用 pyvis 可视化
            net = Network(height="500px", width="100%", directed=True, notebook=False)
            net.from_nx(G)
            net.set_options("""
            {
                "physics": {
                    "barnesHut": {
                        "gravitationalConstant": -8000,
                        "springLength": 200
                    }
                },
                "nodes": {
                    "font": {"size": 14}
                },
                "edges": {
                    "font": {"size": 10},
                    "arrows": {"to": {"enabled": true}}
                }
            }
            """)
            
            # 保存并显示
            html_path = PROJECT_ROOT / "outputs" / "graph_vis.html"
            html_path.parent.mkdir(parents=True, exist_ok=True)
            net.save_graph(str(html_path))
            
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            st.components.v1.html(html_content, height=550, scrolling=True)
            
            # 统计信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("节点数", G.number_of_nodes())
            with col2:
                st.metric("边数", G.number_of_edges())
            with col3:
                st.metric("连通分量", nx.number_weakly_connected_components(G))
                
        except ImportError as e:
            st.error(f"图谱可视化依赖缺失: {e}")
            st.code("pip install pyvis networkx")

# ----------------------------------------------------------------------------
# Tab 4: 提取结果详情
# ----------------------------------------------------------------------------
with tab4:
    st.header("📋 知识提取结果")
    
    extractions = st.session_state.extractions
    
    if not extractions:
        st.info("💡 暂无提取结果")
        if not st.session_state.run_state.stage_parse_done:
            st.warning("👈 请先完成【🚀 解析 PDF】步骤")
        elif not st.session_state.run_state.stage_extract_done:
            st.warning("👈 请先完成【🔍 提取知识】步骤")
    else:
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
                    st.markdown(f"**位置**: 字符 {ext.char_interval.get('start_pos')} - {ext.char_interval.get('end_pos')}")
                if ext.attributes:
                    st.markdown("**属性**:")
                    st.json(ext.attributes)

# ----------------------------------------------------------------------------
# Tab Insights: 抽取洞察
# ----------------------------------------------------------------------------
with tab_insights:
    st.header("🧭 抽取洞察")

    if not st.session_state.markdown_content:
        st.info("💡 暂无解析内容")
        st.warning("👈 请先完成【🚀 解析 PDF】步骤")
    elif not st.session_state.extractions:
        st.info("💡 暂无提取结果")
        st.warning("👈 请先完成【🔍 提取知识】步骤")
    else:
        with st.spinner("📊 正在生成洞察分析..."):
            render_insights(st.session_state.markdown_content, st.session_state.extractions)


# ============================================================================
# 页脚
# ============================================================================
st.divider()
st.caption("GraphRAG 知识问答系统 | Powered by LangExtract + ChromaDB + LangGraph")
