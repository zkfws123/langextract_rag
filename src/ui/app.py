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

load_dotenv(PROJECT_ROOT / ".env")

from src.parsers.mineru_parser import MinerUParser
from src.parsers.local_pdf_parser import LocalPDFParser, PYMUPDF_AVAILABLE
from src.parsers.knowledge_extractor import KnowledgeExtractor
from src.retrieval.vector.chroma_store import ChromaVectorStore
from src.graph.in_memory_store import InMemoryGraphStore
from src.agents import build_agent, agent_query
from src.ui.components import (
    render_pdf_viewer,
    render_markdown_preview,
    render_insights,
    clear_session_state,
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
# Session State 初始化
# ============================================================================
if "vector_store" not in st.session_state:
    st.session_state.vector_store = ChromaVectorStore()
if "graph_store" not in st.session_state:
    st.session_state.graph_store = InMemoryGraphStore()
if "agent_built" not in st.session_state:
    st.session_state.agent_built = False
if "markdown_content" not in st.session_state:
    st.session_state.markdown_content = ""
if "extractions" not in st.session_state:
    st.session_state.extractions = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = b""
if "uploaded_name" not in st.session_state:
    st.session_state.uploaded_name = ""


# ============================================================================
# 侧边栏: 文档上传与解析
# ============================================================================
with st.sidebar:
    st.header("📄 文档管理")
    
    # 解析方式选择
    parser_options = ["MinerU API (推荐)"]
    if PYMUPDF_AVAILABLE:
        parser_options.append("本地 PyMuPDF (备选)")
    parser_choice = st.radio("解析方式", parser_options, index=0)
    
    uploaded_file = st.file_uploader(
        "上传 PDF 文档",
        type=["pdf"],
        help="支持中英文 PDF，建议文件大小 < 20MB"
    )
    
    if uploaded_file:
        st.success(f"已选择: {uploaded_file.name}")
        st.session_state.pdf_bytes = uploaded_file.getvalue()
        st.session_state.uploaded_name = uploaded_file.name
        
        if st.button("🚀 开始解析", type="primary", use_container_width=True):
            with st.spinner("正在解析 PDF..."):
                # 保存上传文件到临时目录
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(st.session_state.pdf_bytes)
                    tmp_path = tmp.name
                
                try:
                    # Step 1: PDF 解析
                    if "MinerU" in parser_choice:
                        st.info("📖 Step 1/3: MinerU PDF 解析中...")
                        parser = MinerUParser()
                        markdown_text = parser.parse_pdf(tmp_path)
                    else:
                        st.info("📖 Step 1/3: 本地 PDF 解析中...")
                        parser = LocalPDFParser()
                        markdown_text = parser.parse_pdf(tmp_path)
                    
                    if not markdown_text:
                        st.error("PDF 解析失败，未获取到内容")
                        st.stop()
                    
                    st.session_state.markdown_content = markdown_text
                    
                    # Step 2: LangExtract 知识提取
                    st.info("🔍 Step 2/3: LangExtract 知识提取中...")
                    extractor = KnowledgeExtractor(
                        doc_id=uploaded_file.name,
                        doc_title=uploaded_file.name
                    )
                    extractions = extractor.extract_from_text(markdown_text)
                    st.session_state.extractions = extractions
                    
                    # Step 3: 存储
                    st.info("💾 Step 3/3: 存储到向量库和图谱...")
                    st.session_state.vector_store.index_extractions(extractions)
                    st.session_state.graph_store.build_from_extractions(extractions)
                    
                    # 构建 Agent
                    build_agent(st.session_state.vector_store, st.session_state.graph_store)
                    st.session_state.agent_built = True
                    
                    st.success(f"✅ 解析完成! 提取了 {len(extractions)} 个知识片段")
                    
                except Exception as e:
                    st.error(f"解析失败: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
                finally:
                    os.unlink(tmp_path)
    
    st.divider()
    if st.button("🗑️ 清空本次解析", use_container_width=True):
        clear_session_state([
            "markdown_content",
            "extractions",
            "chat_history",
            "pdf_bytes",
            "uploaded_name",
        ])
        st.session_state.vector_store = ChromaVectorStore()
        st.session_state.graph_store = InMemoryGraphStore()
        st.session_state.agent_built = False
        st.success("已清空当前解析数据")
    
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
# Tab OCR: PDF vs Markdown
# ----------------------------------------------------------------------------
with tab_ocr:
    st.header("🖼️ OCR 对比")

    if not st.session_state.pdf_bytes and not st.session_state.markdown_content:
        st.info("暂无数据，请先上传并解析 PDF")
    else:
        col_pdf, col_md = st.columns(2)

        with col_pdf:
            st.subheader("PDF 预览")
            render_pdf_viewer(st.session_state.pdf_bytes, height=720)

        with col_md:
            st.subheader("OCR / Markdown 预览")
            render_markdown_preview(st.session_state.markdown_content, max_chars=20000)

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
    
    if not entities:
        st.info("暂无图谱数据，请先上传并解析文档")
    else:
        try:
            from pyvis.network import Network
            import networkx as nx
            
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
        st.info("暂无提取结果，请先上传并解析文档")
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
        st.info("暂无解析内容，请先上传 PDF")
    elif not st.session_state.extractions:
        st.info("暂无提取结果，请先完成抽取")
    else:
        render_insights(st.session_state.markdown_content, st.session_state.extractions)


# ============================================================================
# 页脚
# ============================================================================
st.divider()
st.caption("GraphRAG 知识问答系统 | Powered by LangExtract + ChromaDB + LangGraph")
