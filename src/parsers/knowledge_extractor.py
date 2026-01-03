import os
import re
import textwrap
import time
import logging
from pathlib import Path
from typing import List, Optional, Any, Dict, Iterable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import langextract as lx
from dotenv import load_dotenv
from langextract.providers.openai import OpenAILanguageModel
from langextract.prompt_validation import PromptValidationLevel

from src.graph.models import KnowledgeExtraction
from src.graph.in_memory_store import InMemoryGraphStore
from src.retrieval.vector.chroma_store import ChromaVectorStore
from src.configs.prompts.ziwei_doushu import PROMPT as ZIWEI_PROMPT, EXAMPLES as ZIWEI_EXAMPLES

load_dotenv(override=True)

# 配置日志
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _strip_markdown_fence(text: str) -> str:
    """
    Strip markdown code fence markers (```json ... ```) from model responses.
    
    Some OpenAI-compatible API proxies (like Sonetto with gemini models) 
    wrap JSON responses in markdown code blocks, which breaks langextract's JSON parser.
    """
    if not text:
        return text
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Pattern: ```json ... ``` or ``` ... ```
    # Match: optional json/JSON after opening fence, content, closing fence
    pattern = r'^```(?:json|JSON)?\s*\n?(.*?)\n?```$'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    return text


def _coerce_langextract_payload(content: str) -> str:
    """Best-effort normalize model output to langextract's expected JSON shape.

    langextract expects a JSON object with a top-level `extractions` key.
    Some models/gateways may return:
    - a JSON list (treat as extractions)
    - a JSON object with a different key (entities/items/data)
    - a JSON extraction object instead of a list

    This function does not guarantee correctness, but it prevents hard parser failures
    like: `ResolverParsingError: Content must contain an 'extractions' key.`
    """
    if not content:
        return content

    import json

    stripped = _strip_markdown_fence(content)
    # Some gateways return JSON-like strings with invalid backslash escapes.
    # As a best-effort sanitizer, remove stray backslashes that don't start a valid JSON escape.
    # This prevents hard failures like: Invalid \escape at some position.
    # Note: This is lossy, but preferable to a total parse failure.
    stripped = re.sub(r"\\(?![\\/bfnrt\"]|u[0-9a-fA-F]{4})", "", stripped)
    try:
        parsed = json.loads(stripped)
    except Exception:
        # Not JSON; let langextract handle/raise.
        return stripped

    def _as_list(value: Any) -> list:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    if isinstance(parsed, list):
        parsed = {"extractions": parsed}
    elif isinstance(parsed, dict):
        if "extractions" not in parsed:
            # Common alternative keys from various prompts
            for k in ["entities", "items", "data", "results", "output", "extraction"]:
                if k in parsed:
                    parsed = {"extractions": _as_list(parsed.get(k))}
                    break
            else:
                # If it looks like a single extraction object, wrap it.
                if {"extraction_class", "extraction_text"}.issubset(set(parsed.keys())):
                    parsed = {"extractions": [parsed]}
                else:
                    # Unknown object shape: still satisfy contract with empty list.
                    parsed = {"extractions": []}
    else:
        parsed = {"extractions": []}

    try:
        return json.dumps(parsed, ensure_ascii=False)
    except Exception:
        return stripped


def _resolve_llm_config() -> tuple[str, str, str]:
    """Resolve (api_key, base_url, model_id) at call time.

    Supports UI override via ACTIVE_LLM in {ds, gemini3flash, gemini3pro, sonetto5high, sonetto_gemini3pro}.
    """

    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    default_model = os.getenv("DEFAULT_MODEL", "deepseek-chat")

    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    gemini_base_url = os.getenv("GEMINI_BASE_URL", "")
    gemini_model = os.getenv("GEMINI_MODEL", "")

    sonetto_api_key = os.getenv("SONETTO_API_KEY", "")
    sonetto_base_url = os.getenv("SONETTO_BASE_URL", "")
    sonetto_model_high = os.getenv("SONETTO_MODEL_HIGH", "")
    sonetto_model_gemini = os.getenv("SONETTO_MODEL_GEMINI", "")

    active = (os.getenv("ACTIVE_LLM", "") or "").strip().lower()
    if active == "ds":
        return deepseek_api_key, deepseek_base_url, default_model
    if active == "gemini3flash":
        return gemini_api_key, gemini_base_url, "gemini-3-flash-preview"
    if active == "gemini3pro":
        return gemini_api_key, gemini_base_url, "gemini-3-pro-preview"
    if active == "sonetto5high":
        return sonetto_api_key, sonetto_base_url, sonetto_model_high
    if active == "sonetto_gemini3pro":
        return sonetto_api_key, sonetto_base_url, sonetto_model_gemini

    # Default behavior: prefer Gemini config if provided.
    api_key = gemini_api_key or deepseek_api_key
    base_url = gemini_base_url or deepseek_base_url
    model_id = gemini_model or default_model
    return api_key, base_url, model_id


def _build_openai_language_model(api_key: str, base_url: str, model_id: str, *, force_json: bool) -> OpenAILanguageModel:
    kwargs = None
    if force_json:
        # For OpenAI-compatible gateways, this can reduce non-JSON / empty outputs.
        kwargs = {"response_format": {"type": "json_object"}}
    return OpenAILanguageModel(
        model_id=model_id,
        api_key=api_key,
        base_url=base_url,
        kwargs=kwargs,
    )


# Monkey-patch langextract's format_handler to handle markdown-fenced JSON
# and fix extraction_text type issues (some models return dict instead of string)
def _patch_langextract_json_parser():
    """Patch langextract's JSON parser to strip markdown code fences and fix extraction_text types."""
    try:
        from langextract.core import format_handler
        import json
        
        original_parse_output = format_handler.FormatHandler.parse_output
        
        def _fix_extraction_text(data):
            """Recursively fix extraction_text fields that are dicts/lists instead of strings."""
            if isinstance(data, dict):
                # Check if this is an extraction object with extraction_text
                if "extraction_text" in data:
                    ext_text = data["extraction_text"]

                    # Handle dict type
                    if isinstance(ext_text, dict):
                        # Convert dict to string representation
                        # Try to use a meaningful key like 'text', 'value', 'content', or fallback to json
                        for key in ["text", "value", "content", "name", "术语", "概念"]:
                            if key in ext_text:
                                data["extraction_text"] = str(ext_text[key])
                                break
                        else:
                            # Fallback: convert entire dict to json string
                            data["extraction_text"] = json.dumps(ext_text, ensure_ascii=False)

                    # Handle list type
                    elif isinstance(ext_text, list):
                        # If list is not empty, try to extract meaningful content
                        if ext_text:
                            # If first item is a string, use it
                            if isinstance(ext_text[0], str):
                                data["extraction_text"] = ext_text[0]
                            # If first item is a dict, try to extract text from it
                            elif isinstance(ext_text[0], dict):
                                for key in ["text", "value", "content", "name"]:
                                    if key in ext_text[0]:
                                        data["extraction_text"] = str(ext_text[0][key])
                                        break
                                else:
                                    # Fallback: join all items
                                    data["extraction_text"] = ", ".join(str(item) for item in ext_text)
                            else:
                                # Fallback: join all items
                                data["extraction_text"] = ", ".join(str(item) for item in ext_text)
                        else:
                            # Empty list
                            data["extraction_text"] = ""

                    # Handle other non-standard types
                    elif not isinstance(ext_text, (str, int, float)):
                        # Convert any other type to string
                        data["extraction_text"] = str(ext_text)

                # Recursively process nested dicts
                for key, value in data.items():
                    if isinstance(value, (dict, list)):
                        _fix_extraction_text(value)

            elif isinstance(data, list):
                for item in data:
                    _fix_extraction_text(item)

            return data
        
        def _repair_json_invalid_escapes(s: str) -> str:
            """Best-effort repair for common invalid JSON escapes (e.g. `\m`, `\Q`).

            Some gateways/models emit JSON-like text where backslashes appear before
            non-JSON escape characters, triggering `Invalid \\escape` in json.loads.
            We conservatively convert those sequences to a literal backslash.
            """

            if not s or "\\" not in s:
                return s

            # Valid JSON escape sequences: \\ \/ \" \b \f \n \r \t \uXXXX
            # Replace any other `\X` with `\\X` (i.e. literal backslash + X).
            return re.sub(r"\\(?![\\/\"bfnrtu])", r"\\\\", s)

        def patched_parse_output(self, content: str, *args, **kwargs):
            # Normalize to langextract's expected payload shape.
            content = _coerce_langextract_payload(content)

            # Repair common invalid escapes before any JSON parsing.
            content = _repair_json_invalid_escapes(content)
            
            # Try to pre-process JSON to fix extraction_text types
            try:
                parsed = json.loads(content)
                _fix_extraction_text(parsed)
                content = json.dumps(parsed, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass  # If parsing fails, let original handler deal with it
            
            return original_parse_output(self, content, *args, **kwargs)
        
        format_handler.FormatHandler.parse_output = patched_parse_output
    except Exception:
        # Silently fail if patching doesn't work
        pass


# Apply patch on module load
_patch_langextract_json_parser()


class KnowledgeExtractor:
    """
    LangExtract-powered knowledge extractor with precise char_interval traceability.
    Extracts entities, data metrics, relations, and events from text using LLM.
    """

    def __init__(
        self, 
        doc_id: str, 
        doc_title: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        custom_examples: Optional[List[lx.data.ExampleData]] = None
    ):
        self.doc_id = doc_id
        self.doc_title = doc_title or doc_id

        api_key, base_url, model_id = _resolve_llm_config()
        self._model_config = (api_key, base_url, model_id)
        self.model = _build_openai_language_model(api_key, base_url, model_id, force_json=False)
        
        # Use custom prompt or default
        if custom_prompt:
            # Keep UI/user custom prompt, but enforce a stable output contract.
            self.prompt = textwrap.dedent(custom_prompt).strip() + "\n\n" + textwrap.dedent("""\
                输出格式(非常重要):
                - 只输出 JSON，不要输出任何解释文字/markdown/代码块
                - 顶层必须是一个对象，且必须包含键: \"extractions\"
                - \"extractions\" 的值必须是数组；如果没有可提取内容，返回 {\"extractions\": []}
                """).strip()
        else:
            # Default: use ZiWei DouShu domain-specific extraction contract.
            # This aligns stage-1 classes with downstream graph/relation workflows.
            self.prompt = ZIWEI_PROMPT

        # Use custom examples or build default
        if custom_examples:
            self.examples = custom_examples
        else:
            self.examples = self._build_examples()

    def _build_examples(self) -> List[lx.data.ExampleData]:
        return ZIWEI_EXAMPLES

    def _split_text_to_chunks(self, text: str, *, max_length: int) -> List[Tuple[int, str]]:
        """Split long text to chunks preserving global offsets.

        Returns list of (offset, chunk_text). Offsets are absolute char indices into `text`.

        Strategy:
        - Prefer paragraph-based chunks (split on blank lines).
        - If a single paragraph is too long, fall back to fixed-size slicing.
        """

        if not text:
            return [(0, "")]

        if len(text) <= max_length:
            return [(0, text)]

        chunks: List[Tuple[int, str]] = []

        # Split into paragraphs while keeping separator lengths so offsets stay accurate.
        parts = re.split(r"(\n\s*\n)", text)
        offset = 0
        buf_offset: Optional[int] = None
        buf = ""

        def _flush_buffer():
            nonlocal buf_offset, buf
            if buf:
                chunks.append((buf_offset or 0, buf))
            buf_offset = None
            buf = ""

        for part in parts:
            if part == "":
                continue

            # If it's a blank-line separator, always attach it to the current buffer.
            if re.fullmatch(r"\n\s*\n", part):
                if buf == "":
                    # leading separators: keep offset advancing but don't start a chunk
                    offset += len(part)
                    continue
                # Only add separator if it doesn't blow the chunk.
                if len(buf) + len(part) <= max_length:
                    buf += part
                    offset += len(part)
                    continue
                _flush_buffer()
                offset += len(part)
                continue

            # Normal text paragraph.
            para = part

            if len(para) > max_length:
                # Paragraph itself is too long: flush current buffer, then slice paragraph.
                _flush_buffer()
                start = 0
                while start < len(para):
                    chunk = para[start : start + max_length]
                    chunks.append((offset + start, chunk))
                    start += max_length
                offset += len(para)
                continue

            if buf == "":
                buf_offset = offset
                buf = para
                offset += len(para)
                continue

            if len(buf) + len(para) <= max_length:
                buf += para
                offset += len(para)
                continue

            _flush_buffer()
            buf_offset = offset
            buf = para
            offset += len(para)

        _flush_buffer()

        # Ensure we didn't somehow create empty output.
        return chunks or [(0, text[:max_length])]

    def _dedupe_extractions(self, extractions: List[KnowledgeExtraction]) -> List[KnowledgeExtraction]:
        """Best-effort de-dup across chunk boundaries."""

        seen: set[tuple] = set()
        deduped: List[KnowledgeExtraction] = []

        for ext in extractions:
            key = (
                (ext.extraction_class or "").strip(),
                (ext.extraction_text or "").strip(),
                (ext.char_interval or {}).get("start_pos"),
                (ext.char_interval or {}).get("end_pos"),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(ext)
        return deduped

    def extract_from_text(
        self,
        text: str,
        max_length: int = 8000,
        *,
        enable_chunking: bool = True,
        parallel_workers: Optional[int] = None,
    ) -> List[KnowledgeExtraction]:
        """
        Extract knowledge using LangExtract with full char_interval traceability.

        Prefer full-text coverage:
        - When text is longer than `max_length`, optionally split into chunks.
        - Optionally run chunks in parallel and merge results.
        - Always convert chunk-local char_interval to global char_interval via offset.
        """
        quiet = (os.getenv("EXTRACTION_QUIET", "1").strip().lower() in {"1", "true", "yes", "on"})

        # Decide chunking + parallelism.
        effective_parallel = parallel_workers
        if effective_parallel is None:
            # Default: keep stable single-thread behavior unless explicitly enabled.
            env_parallel = (os.getenv("EXTRACTION_PARALLEL_WORKERS", "").strip() or "")
            if env_parallel.isdigit():
                effective_parallel = max(1, int(env_parallel))
            else:
                effective_parallel = 1

        chunks: List[Tuple[int, str]]
        if enable_chunking and len(text) > max_length:
            chunks = self._split_text_to_chunks(text, max_length=max_length)
            if not quiet:
                logger.info(f"文本过长，启用分块: total_length={len(text):,}, chunks={len(chunks)}")
        else:
            chunks = [(0, text)]

        api_key, base_url, model_id = self._model_config

        attempts = [
            {"force_json": False, "fence_output": True},
            {"force_json": True, "fence_output": False},
            {"force_json": True, "fence_output": True},
        ]

        def _extract_one_chunk(chunk_offset: int, chunk_text: str) -> List[KnowledgeExtraction]:
            if not chunk_text:
                return []

            if not quiet:
                logger.info(
                    f"开始分块提取: model={model_id}, chunk_offset={chunk_offset}, chunk_length={len(chunk_text):,}"
                )

            last_err: Optional[Exception] = None
            result = None
            for attempt_idx, cfg in enumerate(attempts, start=1):
                if not quiet:
                    logger.info(
                        f"  尝试 {attempt_idx}/{len(attempts)}: force_json={cfg['force_json']}, fence_output={cfg['fence_output']}"
                    )
                model = (
                    self.model
                    if not cfg["force_json"]
                    else _build_openai_language_model(api_key, base_url, model_id, force_json=True)
                )
                try:
                    result = lx.extract(
                        text_or_documents=chunk_text,
                        prompt_description=self.prompt,
                        examples=self.examples,
                        model=model,
                        fence_output=cfg["fence_output"],
                        use_schema_constraints=False,
                        prompt_validation_level=PromptValidationLevel.OFF,
                        temperature=0,
                        # Keep langextract internal concurrency disabled; we handle parallelism at chunk level.
                        max_workers=1,
                        show_progress=True,
                    )
                    if not quiet:
                        logger.info(f"  ✓ 分块提取成功（尝试 {attempt_idx}）: {len(result.extractions)}")
                    break
                except (KeyboardInterrupt, SystemExit):
                    logger.warning("检测到中断信号，停止知识提取重试")
                    raise
                except Exception as e:
                    last_err = e
                    error_type = type(e).__name__
                    error_msg = str(e)
                    logger.error(f"  ✗ 分块提取失败（尝试 {attempt_idx}）: {error_type}: {error_msg}")

                    if isinstance(e, RuntimeError) and "cannot schedule new futures after interpreter shutdown" in error_msg:
                        logger.error("解释器正在关闭，终止重试以避免 futures 提交失败")
                        raise

                    if attempt_idx == len(attempts):
                        import traceback

                        logger.error(f"完整错误堆栈:\n{traceback.format_exc()}")

                    if attempt_idx < len(attempts):
                        if not quiet:
                            logger.info("  等待 1 秒后重试...")
                        time.sleep(1.0)
            else:
                assert last_err is not None
                raise last_err

            if result is None:
                return []

            # Some parse errors are swallowed/raised inside langextract; if we reach here,
            # ensure we can still safely post-process.
            try:
                raw_extractions = getattr(result, "extractions", None) or []
            except Exception:
                raw_extractions = []

            # Post-process chunk results into our domain model.

            # Keep ZiWei domain classes intact, but guard against field-name leakage.
            def _normalize_extraction_class(raw: Any) -> tuple[str, Optional[str]]:
                """Return (class_value, original_if_changed). Only fixes obvious invalid values."""
                try:
                    s = ("" if raw is None else str(raw)).strip()
                except Exception:
                    s = ""
                if not s:
                    return "专业术语定义", None
                bad = {"extraction_text", "extraction_class", "char_interval", "attributes"}
                if s in bad:
                    return "专业术语定义", s
                return s, None

            extractions: List[KnowledgeExtraction] = []
            type_error_count = 0

            for idx, ext in enumerate(raw_extractions):
                ext_text = getattr(ext, "extraction_text", "")

                # Normalize extraction_class (but keep ZiWei classes intact).
                norm_class, original_class = _normalize_extraction_class(getattr(ext, "extraction_class", None))

                # Fix extraction_text type issues.
                if not isinstance(ext_text, (str, int, float)):
                    type_error_count += 1
                    try:
                        import json

                        ext_text = json.dumps(ext_text, ensure_ascii=False)
                    except Exception:
                        ext_text = str(ext_text)

                char_interval = None
                try:
                    ci = getattr(ext, "char_interval", None)
                    if ci:
                        char_interval = {
                            "start_pos": ci.start_pos + chunk_offset,
                            "end_pos": ci.end_pos + chunk_offset,
                        }
                except Exception:
                    char_interval = None

                # Preserve original class if we had to normalize it.
                attrs = getattr(ext, "attributes", None) or {}
                if original_class and isinstance(attrs, dict):
                    attrs.setdefault("原始extraction_class", original_class)

                extractions.append(
                    KnowledgeExtraction(
                        doc_id=self.doc_id,
                        doc_title=self.doc_title,
                        extraction_class=norm_class,
                        extraction_text=str(ext_text),
                        char_interval=char_interval,
                        attributes=attrs,
                    )
                )

            if type_error_count > 0 and not quiet:
                logger.warning(f"共发现 {type_error_count} 个类型错误的 extraction_text，已全部修复")

            return extractions

        # Run chunk extraction (optionally parallel) and merge.
        merged: List[KnowledgeExtraction] = []
        if len(chunks) == 1 or effective_parallel <= 1:
            for off, chunk_text in chunks:
                merged.extend(_extract_one_chunk(off, chunk_text))
        else:
            if not quiet:
                logger.info(f"启用并行分块提取: workers={effective_parallel}")
            with ThreadPoolExecutor(max_workers=effective_parallel) as pool:
                futures = [pool.submit(_extract_one_chunk, off, chunk_text) for off, chunk_text in chunks]
                for fut in as_completed(futures):
                    res = fut.result()
                    if not res:
                        continue
                    merged.extend(res)

        # Sort & best-effort de-dup.
        merged.sort(key=lambda e: ((e.char_interval or {}).get("start_pos", 10**18), e.extraction_class, e.extraction_text))
        merged = self._dedupe_extractions(merged)

        if not quiet:
            logger.info(f"✓ 知识提取完成: 成功提取 {len(merged)} 个知识点")
        return merged


def ingest_text_file(
    file_path: Path,
    vector_store: Optional[ChromaVectorStore] = None,
    graph_store: Optional[InMemoryGraphStore] = None,
    doc_id: Optional[str] = None,
    doc_title: Optional[str] = None,
) -> List[KnowledgeExtraction]:
    """Read a text file, extract knowledge, and populate vector + graph stores."""

    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    resolved_doc_id = doc_id or path.stem
    resolved_title = doc_title or path.name
    extractor = KnowledgeExtractor(doc_id=resolved_doc_id, doc_title=resolved_title)
    extractions = extractor.extract_from_text(text)

    if vector_store:
        vector_store.index_extractions(extractions)
    if graph_store:
        graph_store.build_from_extractions(extractions)

    return extractions


def search_knowledge(
    query: str,
    vector_store: Optional[ChromaVectorStore] = None,
    graph_store: Optional[InMemoryGraphStore] = None,
    top_k: int = 5,
    hop: int = 1,
) -> dict:
    """Wrapper that runs both vector search and graph search."""

    vector_results = []
    graph_results = {}
    if vector_store:
        vector_results = vector_store.similarity_search(query, top_k=top_k)
    if graph_store:
        graph_results = graph_store.search(query, hop=hop)
    return {
        "vector_results": vector_results,
        "graph_results": graph_results,
    }
