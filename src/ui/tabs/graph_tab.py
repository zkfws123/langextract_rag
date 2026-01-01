"""知识图谱可视化标签页"""
import streamlit as st
from pathlib import Path
from src.ui.session import SessionManager


def render_graph_tab(session: SessionManager):
    """渲染知识图谱可视化标签页"""
    st.header("🕸️ 知识图谱可视化")
    
    kg = session.graph_store.knowledge_graph
    entities = kg.get("entities", {})
    relations = kg.get("relations", [])
    
    # 显示统计
    if entities:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📍 实体节点", len(entities))
        with col2:
            st.metric("🔗 关系边", len(relations))
    
    if not entities:
        st.info("💡 暂无图谱数据，请先完成知识提取和入库")
        return
    
    try:
        with st.spinner("🔄 正在加载图谱可视化..."):
            try:
                from pyvis.network import Network
                import networkx as nx
            except ImportError as ie:
                st.error(f"❌ 缺少依赖库: {ie}")
                st.code("pip install pyvis networkx")
                return
        
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
            attrs = data.get('attributes', {})
            G.add_node(name, title=f"{entity_type}\n{attrs}", color=color)
        
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
        PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
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
