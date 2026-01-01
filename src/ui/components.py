from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Iterable, Optional

import streamlit as st

from src.ui.insights import build_insights_html


_PDFJS_CACHE: dict[str, str] = {}


def _load_pdfjs_assets() -> tuple[str, str]:
    """Load vendored pdf.js assets from lib/pdfjs.

    We inline them into the component so Chrome won't block plugin-based PDF
    rendering inside Streamlit's sandboxed iframe.
    """

    if "pdfjs" in _PDFJS_CACHE and "worker" in _PDFJS_CACHE:
        return _PDFJS_CACHE["pdfjs"], _PDFJS_CACHE["worker"]

    project_root = Path(__file__).resolve().parents[2]
    pdfjs_path = project_root / "lib" / "pdfjs" / "pdf.min.js"
    worker_path = project_root / "lib" / "pdfjs" / "pdf.worker.min.js"

    pdfjs_code = pdfjs_path.read_text(encoding="utf-8")
    worker_code = worker_path.read_text(encoding="utf-8")

    # Avoid accidentally terminating <script> blocks.
    pdfjs_code = pdfjs_code.replace("</script>", "<\\/script>")
    worker_code = worker_code.replace("</script>", "<\\/script>")

    _PDFJS_CACHE["pdfjs"] = pdfjs_code
    _PDFJS_CACHE["worker"] = worker_code
    return pdfjs_code, worker_code


def render_pdf_viewer(pdf_bytes: bytes, height: int = 720) -> None:
        if not pdf_bytes:
                st.info("暂无 PDF")
                return

        b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        try:
                pdfjs_code, worker_code = _load_pdfjs_assets()
        except Exception as e:
                st.error(f"PDF 预览资源缺失: {e}")
                st.info("请确认已存在 lib/pdfjs/pdf.min.js 和 lib/pdfjs/pdf.worker.min.js")
                return

        worker_json = json.dumps(worker_code)

        pdf_display = f"""
        <div style="border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;">
            <div id="pdf_scroll" style="height:{height}px; overflow:auto; background:#111827;">
                <div id="pdf_container" style="padding: 12px;"></div>
            </div>
        </div>

        <script>
        {pdfjs_code}
        </script>

        <script>
            (function() {{
                const workerCode = {worker_json};
                const workerBlob = new Blob([workerCode], {{ type: 'text/javascript' }});
                const workerUrl = URL.createObjectURL(workerBlob);
                if (window.pdfjsLib) {{
                    window.pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;
                }} else {{
                    const container = document.getElementById('pdf_container');
                    container.innerHTML = '<div style="color:#f87171;">pdf.js 加载失败</div>';
                    return;
                }}

                const b64 = "{b64}";
                function b64ToUint8Array(base64) {{
                    const binary = atob(base64);
                    const len = binary.length;
                    const bytes = new Uint8Array(len);
                    for (let i = 0; i < len; i++) {{
                        bytes[i] = binary.charCodeAt(i);
                    }}
                    return bytes;
                }}

                const data = b64ToUint8Array(b64);
                const container = document.getElementById('pdf_container');
                const scroll = document.getElementById('pdf_scroll');

                function scrollToPage(pageNumber) {{
                    const el = document.getElementById('pdf_page_' + pageNumber);
                    if (el) {{
                        el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                    }}
                }}

                window.addEventListener('message', (event) => {{
                    const msg = event && event.data;
                    if (!msg || msg.type !== 'scrollToPage') return;
                    const page = Number(msg.page);
                    if (!Number.isFinite(page)) return;
                    scrollToPage(page);
                }});

                const loadingTask = window.pdfjsLib.getDocument({{ data }});
                loadingTask.promise.then(async (pdf) => {{
                    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {{
                        const page = await pdf.getPage(pageNum);
                        const viewport = page.getViewport({{ scale: 1.25 }});
                        const canvas = document.createElement('canvas');
                        canvas.id = 'pdf_page_' + pageNum;
                        canvas.style.display = 'block';
                        canvas.style.margin = '0 auto 12px auto';
                        canvas.style.background = '#ffffff';
                        const ctx = canvas.getContext('2d');
                        canvas.width = viewport.width;
                        canvas.height = viewport.height;
                        container.appendChild(canvas);
                        await page.render({{ canvasContext: ctx, viewport }}).promise;
                    }}
                }}).catch((err) => {{
                    container.innerHTML = '<div style="color:#f87171;">PDF 渲染失败: ' + String(err) + '</div>';
                    scroll.scrollTop = 0;
                }});
            }})();
        </script>
        """

        st.components.v1.html(pdf_display, height=height + 24, scrolling=False)


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
