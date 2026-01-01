"""问答标签页"""
import streamlit as st
from src.ui.session import SessionManager
from src.agents import build_agent, agent_query
from src.retrieval.vector.chroma_store import ChromaVectorStore


def render_chat_tab(session: SessionManager, kb_service):
    """渲染问答标签页"""
    st.header("GraphRAG 智能问答")
    
    # 检查是否选择了知识库
    if not session.current_kb_id:
        st.info("👈 请先在左侧选择或创建知识库")
        return
    
    # 检查知识库是否有数据
    kb = kb_service.get_kb(session.current_kb_id)
    if not kb or kb.total_entities == 0:
        st.info("💡 当前知识库为空，请先上传并处理文档")
        return
    
    # 自动恢复 Agent（如果需要）
    if not session.agent_built:
        try:
            # 加载向量库和图谱
            if not session.vector_store:
                collection_name = kb_service.get_collection_name(session.current_kb_id)
                session.vector_store = ChromaVectorStore(collection_name=collection_name)
            
            if not session.graph_store or not session.graph_store.knowledge_graph.get("entities"):
                graph_data = kb_service.get_graph(session.current_kb_id)
                from src.graph.in_memory_store import InMemoryGraphStore
                session.graph_store = InMemoryGraphStore(graph_data)
            
            build_agent(session.vector_store, session.graph_store)
            session.agent_built = True
            st.success("✅ Agent 已自动恢复")
        except Exception as e:
            st.error(f"Agent 自动恢复失败: {e}")
            return
    
    # 显示对话历史
    for msg in session.chat_history:
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
        session.chat_history.append({"role": "user", "content": prompt})
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
            
            session.chat_history.append({
                "role": "assistant",
                "content": answer,
                "evidence": evidence
            })
