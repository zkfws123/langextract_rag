#!/usr/bin/env python
"""Run entity extraction on an OCR'ed markdown document.

- Reads a markdown file
- Runs `KnowledgeExtractor.extract_from_text`
- Prints a short summary and samples
- Saves full results to a JSON file under outputs/

This script *does* call the configured LLM.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from src.parsers.knowledge_extractor import KnowledgeExtractor


DOC_PATH = Path(r"d:\pythonprojects\llamaindex_langextract_rag\outputs\knowledge_bases\57e434ee\documents\09e977e9\content.md")


def _dump_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    if not DOC_PATH.exists():
        raise SystemExit(f"File not found: {DOC_PATH}")

    text = DOC_PATH.read_text(encoding="utf-8")
    print(f"Loaded: {DOC_PATH}")
    print(f"Chars: {len(text)}")

    # Use a stable doc_id so repeated runs can be compared.
    extractor = KnowledgeExtractor(doc_id="ocr_09e977e9", doc_title="OCR文档-飞星棋谱")

    print("\nRunning extraction...")
    extractions = extractor.extract_from_text(text, max_length=8000)

    print("\nDone.")
    print(f"Total extractions: {len(extractions)}")

    # Quick samples
    sample_n = 20
    for i, e in enumerate(extractions[:sample_n], start=1):
        # KnowledgeExtraction is likely a Pydantic model; try model_dump first.
        if hasattr(e, "model_dump"):
            d = e.model_dump()
        elif hasattr(e, "dict"):
            d = e.dict()
        else:
            d = asdict(e)  # best-effort

        print(f"\n[{i}] class={d.get('extraction_class')} text={str(d.get('extraction_text'))[:80]}")
        attrs = d.get("attributes") or {}
        if attrs:
            # print only a few keys
            keys = list(attrs.keys())[:6]
            preview = {k: attrs[k] for k in keys}
            print(f"    attrs={preview}")
        ci = d.get("char_interval")
        if ci:
            print(f"    span={ci.get('start_pos')}-{ci.get('end_pos')}")

    # Save full results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path("outputs") / "runs" / f"ocr_extract_{ts}" / "extractions.json"

    payload = []
    for e in extractions:
        if hasattr(e, "model_dump"):
            payload.append(e.model_dump())
        elif hasattr(e, "dict"):
            payload.append(e.dict())
        else:
            payload.append(asdict(e))

    _dump_json(out_path, payload)
    print(f"\nSaved JSON: {out_path}")


if __name__ == "__main__":
    main()
