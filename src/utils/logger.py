"""
统一日志配置模块
用于记录Agent对话、工具调用、知识图谱查询等关键操作
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class AgentLogger:
    """Agent日志管理器"""
    
    _instance: Optional['AgentLogger'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._setup_logger()
            AgentLogger._initialized = True
    
    def _setup_logger(self):
        """配置日志系统"""
        # 创建日志目录
        log_dir = Path("outputs/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件路径（按日期分文件）
        today = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"agent_chat_{today}.log"
        
        # 创建logger
        self.logger = logging.getLogger("AgentRAG")
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加handler
        if self.logger.handlers:
            return
        
        # 文件handler - 记录所有级别
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # 控制台handler - 只显示INFO及以上
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # 添加handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info("=" * 80)
        self.logger.info("Agent日志系统已启动")
        self.logger.info(f"日志文件: {log_file}")
        self.logger.info("=" * 80)
    
    def log_user_query(self, question: str):
        """记录用户提问"""
        self.logger.info("=" * 80)
        self.logger.info(f"📝 用户提问: {question}")
        self.logger.info("=" * 80)
    
    def log_tool_call(self, tool_name: str, args: dict):
        """记录工具调用"""
        self.logger.info(f"🔧 调用工具: {tool_name}")
        self.logger.debug(f"   参数: {args}")
    
    def log_tool_result(self, tool_name: str, result: str, success: bool = True):
        """记录工具返回结果"""
        status = "✅ 成功" if success else "❌ 失败"
        self.logger.info(f"{status} 工具返回: {tool_name}")
        
        # 截断过长的结果
        if len(result) > 500:
            preview = result[:500] + f"... (共{len(result)}字符)"
        else:
            preview = result
        
        self.logger.debug(f"   结果预览: {preview}")
    
    def log_vector_search(self, query: str, result_count: int):
        """记录向量检索"""
        self.logger.info(f"🔍 向量检索: '{query}' -> 找到 {result_count} 条结果")
    
    def log_graph_search(self, entity: str, has_results: bool):
        """记录图谱检索"""
        status = "找到关联" if has_results else "未找到"
        self.logger.info(f"🕸️  图谱检索: '{entity}' -> {status}")
    
    def log_hybrid_search(self, query: str):
        """记录混合检索"""
        self.logger.info(f"🔄 混合检索: '{query}'")
    
    def log_agent_response(self, answer: str, used_tools: list):
        """记录Agent最终回答"""
        self.logger.info(f"💬 Agent回答: {answer[:200]}{'...' if len(answer) > 200 else ''}")
        if used_tools:
            tools_str = ", ".join(used_tools)
            self.logger.info(f"📊 使用的工具: {tools_str}")
        else:
            self.logger.warning("⚠️  警告: Agent未调用任何工具，可能在随意生成内容！")
    
    def log_no_tool_warning(self):
        """记录未使用工具的警告"""
        self.logger.warning("⚠️  警告: Agent回答时未调用知识库工具，答案可能不准确！")
        self.logger.warning("   建议: 检查Agent是否正确理解问题，或问题是否需要知识库支持")
    
    def debug(self, message: str):
        """调试日志"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """信息日志"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """警告日志"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """错误日志"""
        self.logger.error(message)


# 全局单例
_agent_logger = None


def get_agent_logger() -> AgentLogger:
    """获取Agent日志器单例"""
    global _agent_logger
    if _agent_logger is None:
        _agent_logger = AgentLogger()
    return _agent_logger

