"""设置配置侧边栏"""
import os
import json
import streamlit as st
from src.ui.session import SessionManager
from src.configs import ConfigType, get_config


def render_settings_sidebar(session: SessionManager):
    """渲染设置配置侧边栏"""
    
    st.divider()
    
    # LLM 模型选择
    with st.expander("LLM 模型", expanded=False):
        llm_options = ["ds", "gemini3flash", "gemini3pro", "sonetto5high", "sonetto_gemini3pro"]
        
        active_llm = st.selectbox(
            "LLM 模型",
            llm_options,
            index=llm_options.index(session.active_llm) if session.active_llm in llm_options else 0,
            key="llm_model_selector",
            label_visibility="collapsed",
        )
        
        st.caption(f"当前 ACTIVE_LLM: {session.active_llm}")
        
        if active_llm != session.active_llm:
            session.active_llm = active_llm
            os.environ["ACTIVE_LLM"] = active_llm
            # 切换模型后需要重新构建 Agent
            session.agent_built = False
            st.success(f"已切换 LLM: {active_llm}")
            st.rerun()
    
    # 提取配置
    with st.expander("知识提取配置", expanded=False):
        st.markdown("**文档类型选择**")
        
        # 文档类型选择
        doc_type_options = {
            ConfigType.get_display_name(ConfigType.ZIWEI_DOUSHU): ConfigType.ZIWEI_DOUSHU,
            ConfigType.get_display_name(ConfigType.GENERAL): ConfigType.GENERAL,
        }
        
        selected_type_name = st.selectbox(
            "文档类型",
            list(doc_type_options.keys()),
            index=0 if session.selected_doc_type == ConfigType.ZIWEI_DOUSHU else 1,
            key="doc_type_selector",
            label_visibility="collapsed"
        )
        
        # 检测类型变化，自动加载配置
        new_type = doc_type_options[selected_type_name]
        if new_type != session.selected_doc_type:
            session.selected_doc_type = new_type
            # 加载对应的默认配置
            default_prompt, default_examples = get_config(new_type)
            session.extraction_prompt = default_prompt
            
            # 转换 examples 为 JSON 格式
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
            session.extraction_examples_json = json.dumps(examples_json, ensure_ascii=False, indent=2)
            session.extraction_examples_parsed = examples_json
            st.success(f"✅ 已切换到 {selected_type_name} 配置")
            st.rerun()
        
        st.divider()
        st.markdown("**自定义提取 Prompt**")
        
        # 如果没有设置过，使用当前类型的默认配置
        if not session.extraction_prompt:
            default_prompt, default_examples = get_config(session.selected_doc_type)
            session.extraction_prompt = default_prompt
            # 转换 examples
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
            session.extraction_examples_json = json.dumps(examples_json, ensure_ascii=False, indent=2)
            session.extraction_examples_parsed = examples_json
        
        custom_prompt = st.text_area(
            "Extraction Prompt",
            value=session.extraction_prompt,
            height=200,
            help="描述要从文档中提取的知识类型和要求",
            label_visibility="collapsed"
        )
        
        if st.button("💾 保存 Prompt", use_container_width=True):
            session.extraction_prompt = custom_prompt
            st.success("✅ Prompt 已更新")
        
        st.divider()
        st.markdown("**Few-Shot Examples (JSON格式)**")
        st.caption("提供1-3个示例，教模型输出格式")
        
        custom_examples_json = st.text_area(
            "Examples JSON",
            value=session.extraction_examples_json,
            height=250,
            help="JSON数组格式，每个对象包含text和extractions字段",
            label_visibility="collapsed"
        )
        
        if st.button("💾 保存 Examples", use_container_width=True):
            try:
                examples_data = json.loads(custom_examples_json)
                session.extraction_examples_json = custom_examples_json
                session.extraction_examples_parsed = examples_data
                st.success(f"✅ Examples 已更新（{len(examples_data)}个）")
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON 格式错误: {e}")
