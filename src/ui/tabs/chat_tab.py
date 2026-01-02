"""问答标签页"""
import streamlit as st
from src.ui.session import SessionManager
from src.agents import build_agent, agent_query
from src.retrieval.vector.chroma_store import ChromaVectorStore


def render_chat_tab(session: SessionManager, kb_service):
    """渲染问答标签页"""
    # 检查是否选择了知识库
    if not session.current_kb_id:
        st.header("GraphRAG 智能问答")
        st.info("👈 请先在左侧选择或创建知识库")
        return

    # 检查知识库是否有数据
    kb = kb_service.get_kb(session.current_kb_id)
    if not kb:
        st.header("GraphRAG 智能问答")
        st.error("❌ 知识库不存在")
        return

    # 显示标题和当前知识库名称
    st.header("GraphRAG 智能问答")
    st.markdown(f"**📚 当前知识库：** `{kb.name}` (ID: `{session.current_kb_id[:8]}...`)")

    if kb.total_entities == 0:
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
            # 如果是助手消息且有错误标记，显示错误提示
            if msg["role"] == "assistant" and msg.get("error") == "NO_TOOL_CALLED":
                st.error("❌ **错误：Agent未调用知识库工具**")
                st.error("⚠️ 该回答没有证据溯源，不可信！")

            st.markdown(msg["content"])

            if msg.get("evidence"):
                with st.expander("📎 查看证据溯源"):
                    for ev in msg["evidence"]:
                        if ev.get("type") == "result":
                            st.code(ev.get("content", ""), language="text")
            elif msg["role"] == "assistant" and not msg.get("error"):
                # 如果是助手消息，没有证据也没有错误标记，显示警告
                st.warning("⚠️ 警告：该回答缺少证据溯源")
    
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
                error = result.get("error", None)

            # 检查是否有错误（未调用工具）
            if error == "NO_TOOL_CALLED":
                st.error("❌ **错误：Agent未调用知识库工具**")
                st.error("⚠️ 该回答没有证据溯源，不可信！")
                st.warning("💡 建议：请重新提问或换个问法，确保问题与知识库内容相关")

            st.markdown(answer)

            if evidence:
                with st.expander("📎 查看证据溯源"):
                    for ev in evidence:
                        if ev.get("type") == "result":
                            st.code(ev.get("content", ""), language="text")
            elif not error:
                # 如果没有证据也没有错误标记，也显示警告
                st.warning("⚠️ 警告：该回答缺少证据溯源")

            session.chat_history.append({
                "role": "assistant",
                "content": answer,
                "evidence": evidence,
                "error": error
            })
