from __future__ import annotations

import base64
from typing import Any, Iterable, Optional

import streamlit as st

from src.ui.insights import build_insights_html


def render_pdf_viewer(pdf_bytes: bytes, height: int = 720) -> None:
    if not pdf_bytes:
        st.info("暂无 PDF")
        return

    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    pdf_display = f"""
    <iframe
      src="data:application/pdf;base64,{b64}"
      width="100%"
      height="{height}"
      style="border: 1px solid #e5e7eb; border-radius: 10px;"
      type="application/pdf"
    ></iframe>
    """
    st.components.v1.html(pdf_display, height=height + 20, scrolling=True)


def render_markdown_preview(markdown_text: str, max_chars: int = 20000) -> None:
    if not markdown_text:
        st.info("暂无解析内容")
        return

    shown = markdown_text[:max_chars]
    st.markdown(shown)
    if len(markdown_text) > max_chars:
        st.info(f"内容过长，仅显示前 {max_chars} 字符 (共 {len(markdown_text)} 字符)")


def render_insights(markdown_text: str, extractions: Iterable[Any]) -> None:
    if not markdown_text:
        st.info("暂无源文档内容")
        return

    html = build_insights_html(markdown_text, extractions)
    st.components.v1.html(html, height=760, scrolling=False)


def clear_session_state(keys: Optional[list[str]] = None) -> None:
    if keys is None:
        keys = []
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]
