"""UI log sink for Streamlit.

This module provides a lightweight logging handler that writes log lines into
Streamlit `st.session_state`, so the frontend can render a live log panel.

Design goals:
- Best-effort / non-intrusive: never crash the app on logging.
- Not tied to a specific page: any module can call `setup_ui_logger()`.
"""

from __future__ import annotations

import logging
from typing import Optional

import streamlit as st

try:
    # Streamlit >= 1.25
    from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore
except Exception:  # pragma: no cover
    try:
        # Older / alternative import path
        from streamlit.runtime.scriptrunner.script_run_context import (  # type: ignore
            get_script_run_ctx,
        )
    except Exception:  # pragma: no cover
        get_script_run_ctx = None  # type: ignore


class UILogHandler(logging.Handler):
    def __init__(self, *, max_lines_key: str = "ui_logs_max_lines", buffer_key: str = "ui_logs"):
        super().__init__()
        self._max_lines_key = max_lines_key
        self._buffer_key = buffer_key

    def emit(self, record: logging.LogRecord) -> None:
        # Avoid touching Streamlit session_state from background threads.
        # Otherwise Streamlit will emit: "missing ScriptRunContext" warnings.
        try:
            if get_script_run_ctx is not None and get_script_run_ctx() is None:
                return
        except Exception:
            return

        try:
            msg = self.format(record)
        except Exception:
            try:
                msg = record.getMessage()
            except Exception:
                msg = str(record)

        try:
            if self._buffer_key not in st.session_state:
                st.session_state[self._buffer_key] = []
            st.session_state[self._buffer_key].append(msg)

            max_lines = int(st.session_state.get(self._max_lines_key, 500) or 500)
            if max_lines and len(st.session_state[self._buffer_key]) > max_lines:
                st.session_state[self._buffer_key] = st.session_state[self._buffer_key][-max_lines:]
        except Exception:
            # Never fail UI due to logging.
            return


def setup_ui_logger(
    *,
    logger_name_prefix: Optional[str] = "src.",
    level: int = logging.INFO,
    fmt: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> None:
    """Attach a `UILogHandler` to project loggers.

    This is safe to call multiple times.
    """

    handler = UILogHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S"))

    # Attach to root so we catch most logs; filter by name prefix at display time.
    root = logging.getLogger()
    already = any(isinstance(h, UILogHandler) for h in root.handlers)
    if not already:
        root.addHandler(handler)

    # Ensure root level is not higher than desired.
    if root.level > level:
        root.setLevel(level)

    # Optionally ensure common project loggers aren't silenced.
    if logger_name_prefix:
        logging.getLogger(logger_name_prefix.rstrip("."))
