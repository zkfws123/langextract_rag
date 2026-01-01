"""标签页组件"""
from .preview_tab import render_preview_tab
from .ocr_tab import render_ocr_tab
from .extractions_tab import render_extractions_tab
from .graph_tab import render_graph_tab
from .insights_tab import render_insights_tab
from .chat_tab import render_chat_tab
from .documents_tab import render_documents_tab

__all__ = [
    "render_preview_tab",
    "render_ocr_tab",
    "render_extractions_tab",
    "render_graph_tab",
    "render_insights_tab",
    "render_chat_tab",
    "render_documents_tab",
]
