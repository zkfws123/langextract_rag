"""
Per-document run cache layer (DocumentRun).

Stores multi-stage artifacts under outputs/runs/<doc_hash>/:
 - source.pdf
 - mineru_result.zip
 - markdown_pages.json       (list[str]; one entry per page)
 - page_offsets.json         (list[int]; char-start of each page in full markdown)
 - markdown_full.md
 - extractions.json          (list of KnowledgeExtraction as dicts)
 - graph.json                (entities + relations for InMemoryGraphStore)
 - run_state.json            (stage completions, timestamps)

Supports multiple docs simultaneously; caller passes doc_hash.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

_CACHE_ROOT = Path(__file__).resolve().parents[2] / "outputs" / "runs"


def doc_hash(pdf_bytes: bytes) -> str:
    """Return sha256[:12] of PDF bytes as document identifier."""
    return hashlib.sha256(pdf_bytes).hexdigest()[:12]


@dataclass
class RunState:
    """Tracks which stages are done for a document run."""

    doc_hash: str
    doc_name: str = ""
    stage_parse_done: bool = False
    stage_extract_done: bool = False
    stage_index_done: bool = False
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "doc_hash": self.doc_hash,
            "doc_name": self.doc_name,
            "stage_parse_done": self.stage_parse_done,
            "stage_extract_done": self.stage_extract_done,
            "stage_index_done": self.stage_index_done,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RunState":
        return cls(
            doc_hash=d.get("doc_hash", ""),
            doc_name=d.get("doc_name", ""),
            stage_parse_done=d.get("stage_parse_done", False),
            stage_extract_done=d.get("stage_extract_done", False),
            stage_index_done=d.get("stage_index_done", False),
            updated_at=d.get("updated_at", ""),
        )


class DocumentRunCache:
    """Handles loading/saving all artifacts for one doc run."""

    def __init__(self, doc_hash: str, root: Optional[Path] = None):
        self.doc_hash = doc_hash
        self._root = (root or _CACHE_ROOT) / doc_hash
        self._root.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # Paths
    # --------------------------------------------------
    @property
    def pdf_path(self) -> Path:
        return self._root / "source.pdf"

    @property
    def zip_path(self) -> Path:
        return self._root / "mineru_result.zip"

    @property
    def pages_path(self) -> Path:
        return self._root / "markdown_pages.json"

    @property
    def offsets_path(self) -> Path:
        return self._root / "page_offsets.json"

    @property
    def full_md_path(self) -> Path:
        return self._root / "markdown_full.md"

    @property
    def extractions_path(self) -> Path:
        return self._root / "extractions.json"

    @property
    def graph_path(self) -> Path:
        return self._root / "graph.json"

    @property
    def state_path(self) -> Path:
        return self._root / "run_state.json"

    # --------------------------------------------------
    # RunState
    # --------------------------------------------------
    def load_state(self) -> RunState:
        if self.state_path.exists():
            return RunState.from_dict(json.loads(self.state_path.read_text(encoding="utf-8")))
        return RunState(doc_hash=self.doc_hash)

    def save_state(self, state: RunState) -> None:
        state.updated_at = datetime.utcnow().isoformat(timespec="seconds")
        self.state_path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    # --------------------------------------------------
    # PDF
    # --------------------------------------------------
    def save_pdf(self, pdf_bytes: bytes) -> None:
        self.pdf_path.write_bytes(pdf_bytes)

    def load_pdf(self) -> Optional[bytes]:
        if self.pdf_path.exists():
            return self.pdf_path.read_bytes()
        return None

    # --------------------------------------------------
    # MinerU zip
    # --------------------------------------------------
    def save_zip(self, zip_bytes: bytes) -> None:
        self.zip_path.write_bytes(zip_bytes)

    def load_zip(self) -> Optional[bytes]:
        if self.zip_path.exists():
            return self.zip_path.read_bytes()
        return None

    # --------------------------------------------------
    # Markdown pages
    # --------------------------------------------------
    def save_pages(self, pages: list[str], offsets: list[int]) -> None:
        self.pages_path.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
        self.offsets_path.write_text(json.dumps(offsets), encoding="utf-8")
        full_md = "\n".join(pages)
        self.full_md_path.write_text(full_md, encoding="utf-8")

    def load_pages(self) -> Optional[tuple[list[str], list[int], str]]:
        """Return (pages, offsets, full_md) if cached."""
        if self.pages_path.exists() and self.offsets_path.exists() and self.full_md_path.exists():
            pages = json.loads(self.pages_path.read_text(encoding="utf-8"))
            offsets = json.loads(self.offsets_path.read_text(encoding="utf-8"))
            full_md = self.full_md_path.read_text(encoding="utf-8")
            return pages, offsets, full_md
        return None

    # --------------------------------------------------
    # Extractions
    # --------------------------------------------------
    def save_extractions(self, extractions: list[dict]) -> None:
        self.extractions_path.write_text(json.dumps(extractions, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_extractions(self) -> Optional[list[dict]]:
        if self.extractions_path.exists():
            return json.loads(self.extractions_path.read_text(encoding="utf-8"))
        return None

    # --------------------------------------------------
    # Graph
    # --------------------------------------------------
    def save_graph(self, graph: dict) -> None:
        self.graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_graph(self) -> Optional[dict]:
        if self.graph_path.exists():
            return json.loads(self.graph_path.read_text(encoding="utf-8"))
        return None

    # --------------------------------------------------
    # Clear
    # --------------------------------------------------
    def clear(self) -> None:
        """Delete entire run cache for this doc."""
        if self._root.exists():
            shutil.rmtree(self._root, ignore_errors=True)


def list_cached_runs(root: Optional[Path] = None) -> list[RunState]:
    """Return list of RunState for all cached docs."""
    root = root or _CACHE_ROOT
    if not root.exists():
        return []
    runs: list[RunState] = []
    for subdir in root.iterdir():
        if subdir.is_dir():
            cache = DocumentRunCache(subdir.name, root=root.parent / root.name)
            runs.append(cache.load_state())
    return runs
