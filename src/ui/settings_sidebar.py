"""设置配置侧边栏"""
import os
import json
import streamlit as st
from src.ui.session import SessionManager
from src.configs import ConfigType, get_config
from src.utils.config_manager import APIConfigManager


def render_settings_sidebar(session: SessionManager):
    """渲染设置配置侧边栏"""
    
    st.divider()
    
    # LLM 模型选择
    with st.expander("LLM 模型", expanded=False):
        llm_options = ["openai", "deepseek", "gemini", "custom"]
        llm_labels = {
            "openai": "OpenAI (gpt-4o)",
            "deepseek": "DeepSeek (deepseek-chat)",
            "gemini": "Google Gemini (gemini-2.0-flash-exp)",
            "custom": "自定义 OpenAI 兼容 API"
        }

        active_llm = st.selectbox(
            "LLM 模型",
            llm_options,
            format_func=lambda x: llm_labels[x],
            index=llm_options.index(session.active_llm) if session.active_llm in llm_options else 1,
            key="llm_model_selector",
            label_visibility="collapsed",
        )

        st.caption(f"当前 ACTIVE_LLM: {session.active_llm}")

        if active_llm != session.active_llm:
            session.active_llm = active_llm
            os.environ["ACTIVE_LLM"] = active_llm
            # 切换模型后需要重新构建 Agent
            session.agent_built = False
            st.success(f"已切换 LLM: {llm_labels[active_llm]}")
            st.rerun()
    
    # 提取配置
    with st.expander("知识提取配置", expanded=False):
        st.markdown("**并行分块提取**")

        parallel_enabled = st.toggle(
            "启用并行",
            value=session.extraction_parallel_enabled,
            help="开启后会并行处理分块提取（速度更快，但更吃资源）",
            key="extraction_parallel_enabled",
        )

        workers = st.number_input(
            "Workers",
            min_value=2,
            max_value=16,
            value=int(session.extraction_parallel_workers or 4),
            step=1,
            disabled=not parallel_enabled,
            help="并行 worker 数量（建议 2~8）",
            key="extraction_parallel_workers",
        )

        # Also mirror to env so non-UI codepaths can reuse.
        if parallel_enabled:
            os.environ["EXTRACTION_PARALLEL_WORKERS"] = str(int(workers))
        else:
            os.environ["EXTRACTION_PARALLEL_WORKERS"] = "1"

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

    # API 配置
    with st.expander("🔑 API 配置", expanded=False):
        st.markdown("**配置 LLM、Embedding 和 OCR 服务**")
        st.caption("优先级：UI 配置 > .env 文件")

        # 获取当前配置
        config = session.api_config

        # 显示/隐藏 API Key 开关
        show_keys = st.toggle(
            "显示完整 API Key",
            value=session.api_config_show_keys,
            help="开启后显示完整 API Key，否则用 *** 遮挡",
            key="show_api_keys_toggle"
        )
        session.api_config_show_keys = show_keys

        def mask_key(key: str) -> str:
            """遮挡 API Key"""
            if not key or show_keys:
                return key
            if len(key) <= 8:
                return "***"
            return f"{key[:4]}...{key[-4:]}"

        # LLM 配置
        st.divider()
        st.markdown("**🤖 LLM 配置**")

        # OpenAI
        with st.container():
            st.caption("OpenAI")
            openai_api_key = st.text_input(
                "API Key",
                value=config["llm"]["openai"]["api_key"],
                type="password" if not show_keys else "default",
                key="openai_api_key",
                placeholder="sk-..."
            )
            openai_base_url = st.text_input(
                "Base URL",
                value=config["llm"]["openai"]["base_url"],
                key="openai_base_url",
                placeholder="https://api.openai.com/v1"
            )
            openai_model = st.text_input(
                "Model",
                value=config["llm"]["openai"]["model"],
                key="openai_model",
                placeholder="gpt-4o"
            )
            config["llm"]["openai"]["api_key"] = openai_api_key
            config["llm"]["openai"]["base_url"] = openai_base_url
            config["llm"]["openai"]["model"] = openai_model

        # DeepSeek
        with st.container():
            st.caption("DeepSeek")
            ds_api_key = st.text_input(
                "API Key",
                value=config["llm"]["deepseek"]["api_key"],
                type="password" if not show_keys else "default",
                key="ds_api_key",
                placeholder="sk-..."
            )
            ds_base_url = st.text_input(
                "Base URL",
                value=config["llm"]["deepseek"]["base_url"],
                key="ds_base_url",
                placeholder="https://api.deepseek.com/v1"
            )
            ds_model = st.text_input(
                "Model",
                value=config["llm"]["deepseek"]["model"],
                key="ds_model",
                placeholder="deepseek-chat"
            )
            config["llm"]["deepseek"]["api_key"] = ds_api_key
            config["llm"]["deepseek"]["base_url"] = ds_base_url
            config["llm"]["deepseek"]["model"] = ds_model

        # Gemini
        with st.container():
            st.caption("Google Gemini")
            gemini_api_key = st.text_input(
                "API Key",
                value=config["llm"]["gemini"]["api_key"],
                type="password" if not show_keys else "default",
                key="gemini_api_key",
                placeholder="AIza..."
            )
            gemini_base_url = st.text_input(
                "Base URL",
                value=config["llm"]["gemini"]["base_url"],
                key="gemini_base_url",
                placeholder="https://generativelanguage.googleapis.com/v1beta"
            )
            gemini_model = st.text_input(
                "Model",
                value=config["llm"]["gemini"]["model"],
                key="gemini_model",
                placeholder="gemini-2.0-flash-exp"
            )
            config["llm"]["gemini"]["api_key"] = gemini_api_key
            config["llm"]["gemini"]["base_url"] = gemini_base_url
            config["llm"]["gemini"]["model"] = gemini_model

        # Custom OpenAI-compatible API
        with st.container():
            st.caption("自定义 OpenAI 兼容 API")
            custom_name = st.text_input(
                "名称",
                value=config["llm"]["custom"]["name"],
                key="custom_name",
                placeholder="自定义 API"
            )
            custom_api_key = st.text_input(
                "API Key",
                value=config["llm"]["custom"]["api_key"],
                type="password" if not show_keys else "default",
                key="custom_api_key",
                placeholder="sk-..."
            )
            custom_base_url = st.text_input(
                "Base URL",
                value=config["llm"]["custom"]["base_url"],
                key="custom_base_url",
                placeholder="https://api.example.com/v1"
            )
            custom_model = st.text_input(
                "Model",
                value=config["llm"]["custom"]["model"],
                key="custom_model",
                placeholder="model-name"
            )
            config["llm"]["custom"]["name"] = custom_name
            config["llm"]["custom"]["api_key"] = custom_api_key
            config["llm"]["custom"]["base_url"] = custom_base_url
            config["llm"]["custom"]["model"] = custom_model

        # Embedding 配置
        st.divider()
        st.markdown("**🔍 Embedding 配置**")

        with st.container():
            st.caption("DashScope (阿里云)")
            dashscope_api_key = st.text_input(
                "API Key",
                value=config["embedding"]["dashscope"]["api_key"],
                type="password" if not show_keys else "default",
                key="dashscope_api_key",
                placeholder="sk-..."
            )
            dashscope_base_url = st.text_input(
                "Base URL",
                value=config["embedding"]["dashscope"]["base_url"],
                key="dashscope_base_url",
                placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            dashscope_model = st.text_input(
                "Model",
                value=config["embedding"]["dashscope"]["model"],
                key="dashscope_model",
                placeholder="text-embedding-v4"
            )
            config["embedding"]["dashscope"]["api_key"] = dashscope_api_key
            config["embedding"]["dashscope"]["base_url"] = dashscope_base_url
            config["embedding"]["dashscope"]["model"] = dashscope_model

        # OCR 配置
        st.divider()
        st.markdown("**📄 OCR 配置**")

        with st.container():
            st.caption("MinerU")
            mineru_api_key = st.text_input(
                "API Key",
                value=config["ocr"]["mineru"]["api_key"],
                type="password" if not show_keys else "default",
                key="mineru_api_key",
                placeholder="your_mineru_key"
            )
            mineru_base_url = st.text_input(
                "Base URL",
                value=config["ocr"]["mineru"]["base_url"],
                key="mineru_base_url",
                placeholder="https://mineru.net"
            )
            config["ocr"]["mineru"]["api_key"] = mineru_api_key
            config["ocr"]["mineru"]["base_url"] = mineru_base_url

        # 保存按钮
        st.divider()
        if st.button("💾 保存 API 配置", use_container_width=True, type="primary"):
            session.api_config = config
            if session.save_api_config():
                st.success("✅ API 配置已保存到 outputs/api_config.json")
                # 切换配置后需要重新构建 Agent
                session.agent_built = False
            else:
                st.error("❌ 保存配置失败")
