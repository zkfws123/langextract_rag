"""API 配置管理工具 - 持久化到 JSON 文件"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = Path("outputs/api_config.json")


class APIConfigManager:
    """API 配置管理器 - 负责配置的加载、保存和验证"""
    
    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """获取默认配置结构"""
        return {
            "llm": {
                "openai": {
                    "api_key": "",
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4o"
                },
                "deepseek": {
                    "api_key": "",
                    "base_url": "https://api.deepseek.com/v1",
                    "model": "deepseek-chat"
                },
                "gemini": {
                    "api_key": "",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta",
                    "model": "gemini-2.0-flash-exp"
                },
                "custom": {
                    "api_key": "",
                    "base_url": "",
                    "model": "",
                    "name": "自定义 OpenAI 兼容 API"
                }
            },
            "embedding": {
                "dashscope": {
                    "api_key": "",
                    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "model": "text-embedding-v4"
                }
            },
            "ocr": {
                "mineru": {
                    "api_key": "",
                    "base_url": "https://mineru.net"
                }
            }
        }
    
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """从文件加载配置，如果文件不存在则返回默认配置"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.info(f"✅ 已加载 API 配置: {CONFIG_FILE}")
                    return config
            else:
                logger.info("📝 配置文件不存在，使用默认配置")
                return APIConfigManager.get_default_config()
        except Exception as e:
            logger.error(f"❌ 加载配置失败: {e}")
            return APIConfigManager.get_default_config()
    
    @staticmethod
    def save_config(config: Dict[str, Any]) -> bool:
        """保存配置到文件"""
        try:
            # 确保目录存在
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存配置
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 配置已保存: {CONFIG_FILE}")
            return True
        except Exception as e:
            logger.error(f"❌ 保存配置失败: {e}")
            return False
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> tuple[bool, str]:
        """验证配置有效性"""
        try:
            # 检查必需的顶层键
            required_keys = ["llm", "embedding", "ocr"]
            for key in required_keys:
                if key not in config:
                    return False, f"缺少必需的配置项: {key}"
            
            # 检查 LLM 配置
            if "deepseek" not in config["llm"]:
                return False, "缺少 DeepSeek LLM 配置"
            
            # 检查 Embedding 配置
            if "dashscope" not in config["embedding"]:
                return False, "缺少 DashScope Embedding 配置"
            
            return True, "配置验证通过"
        except Exception as e:
            return False, f"配置验证失败: {str(e)}"
    
    @staticmethod
    def merge_with_env(config: Dict[str, Any]) -> Dict[str, Any]:
        """将 UI 配置与环境变量合并（UI 配置优先）"""
        merged = config.copy()

        # OpenAI
        if not merged["llm"]["openai"]["api_key"]:
            merged["llm"]["openai"]["api_key"] = os.getenv("OPENAI_API_KEY", "")
        if not merged["llm"]["openai"]["base_url"]:
            merged["llm"]["openai"]["base_url"] = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if not merged["llm"]["openai"]["model"]:
            merged["llm"]["openai"]["model"] = os.getenv("OPENAI_MODEL", "gpt-4o")

        # DeepSeek
        if not merged["llm"]["deepseek"]["api_key"]:
            merged["llm"]["deepseek"]["api_key"] = os.getenv("DEEPSEEK_API_KEY", "")
        if not merged["llm"]["deepseek"]["base_url"]:
            merged["llm"]["deepseek"]["base_url"] = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        if not merged["llm"]["deepseek"]["model"]:
            merged["llm"]["deepseek"]["model"] = os.getenv("DEFAULT_MODEL", "deepseek-chat")

        # Gemini
        if not merged["llm"]["gemini"]["api_key"]:
            merged["llm"]["gemini"]["api_key"] = os.getenv("GEMINI_API_KEY", "")
        if not merged["llm"]["gemini"]["base_url"]:
            merged["llm"]["gemini"]["base_url"] = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
        if not merged["llm"]["gemini"]["model"]:
            merged["llm"]["gemini"]["model"] = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

        # Custom (不从环境变量读取，仅用户手动配置)

        # DashScope Embedding
        if not merged["embedding"]["dashscope"]["api_key"]:
            merged["embedding"]["dashscope"]["api_key"] = os.getenv("DASHSCOPE_API_KEY", "")
        if not merged["embedding"]["dashscope"]["base_url"]:
            merged["embedding"]["dashscope"]["base_url"] = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        if not merged["embedding"]["dashscope"]["model"]:
            merged["embedding"]["dashscope"]["model"] = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")

        # MinerU OCR
        if not merged["ocr"]["mineru"]["api_key"]:
            merged["ocr"]["mineru"]["api_key"] = os.getenv("MINERU_API_KEY", "")
        if not merged["ocr"]["mineru"]["base_url"]:
            merged["ocr"]["mineru"]["base_url"] = os.getenv("MINERU_BASE_URL", "https://mineru.net")

        return merged

