"""知识库管理模块"""
from .models import KnowledgeBase, Document, KBConfig, KBStatus, DocumentStatus
from .kb_service import KnowledgeBaseService, get_kb_service

__all__ = [
    "KnowledgeBase", 
    "Document", 
    "KBConfig", 
    "KBStatus", 
    "DocumentStatus",
    "KnowledgeBaseService",
    "get_kb_service"
]
