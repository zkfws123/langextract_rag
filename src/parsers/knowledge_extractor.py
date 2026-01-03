import os
import re
import textwrap
import time
import logging
from pathlib import Path
from typing import List, Optional, Any, Dict

import langextract as lx
from dotenv import load_dotenv
from langextract.providers.openai import OpenAILanguageModel
from langextract.prompt_validation import PromptValidationLevel

from src.graph.models import KnowledgeExtraction
from src.graph.in_memory_store import InMemoryGraphStore
from src.retrieval.vector.chroma_store import ChromaVectorStore

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
        
        def patched_parse_output(self, content: str, *args, **kwargs):
            # Normalize to langextract's expected payload shape.
            content = _coerce_langextract_payload(content)
            
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
            self.prompt = textwrap.dedent("""\
                从文档中提取以下结构化知识:
                
                - 实体: 人物、机构、地点、时间、概念、技术术语
                - 数据指标: 数值、百分比、统计数据
                - 关系描述: 实体之间的关系（合作、隶属、引用等）
                - 事件: 重要事件和行为
                
                要求:
                1. extraction_text 必须是原文的精确子串
                2. 为每个提取添加丰富的属性信息
                3. 关系类型必须在 attributes 中标注涉及的主体
                4. 保持原文出现顺序

                输出格式(非常重要):
                - 只输出 JSON，不要输出任何解释文字/markdown/代码块
                - 顶层必须是一个对象，且必须包含键: "extractions"
                - "extractions" 的值必须是数组；如果没有可提取内容，返回 {"extractions": []}
                """)
        
        # Use custom examples or build default
        if custom_examples:
            self.examples = custom_examples
        else:
            self.examples = self._build_examples()

    def _build_examples(self) -> List[lx.data.ExampleData]:
        example_text = textwrap.dedent("""\
            # 人工智能发展报告
            
            ## 作者
            张三（清华大学）、李四（北京大学）
            
            ## 摘要
            本报告分析了2024年人工智能的发展趋势。研究显示，大模型参数量增长了300%，
            推理成本下降了50%。清华大学与北京大学联合开展了此项研究。
            """).strip()
        example_extractions = [
            lx.data.Extraction(
                extraction_class="实体",
                extraction_text="张三",
                attributes={"类型": "人物", "机构": "清华大学"}
            ),
            lx.data.Extraction(
                extraction_class="实体",
                extraction_text="清华大学",
                attributes={"类型": "机构", "类别": "高校"}
            ),
            lx.data.Extraction(
                extraction_class="数据指标",
                extraction_text="增长了300%",
                attributes={"指标": "大模型参数量", "类型": "增长率"}
            ),
            lx.data.Extraction(
                extraction_class="关系描述",
                extraction_text="清华大学与北京大学联合开展了此项研究",
                attributes={
                    "类型": "合作关系",
                    "主体1": "清华大学",
                    "主体2": "北京大学",
                    "关系": "联合研究"
                }
            ),
        ]
        return [lx.data.ExampleData(text=example_text, extractions=example_extractions)]

    def extract_from_text(self, text: str, max_length: int = 8000) -> List[KnowledgeExtraction]:
        """
        Extract knowledge using LangExtract with full char_interval traceability.

        使用简单的单次抽取策略（参考之前的稳定版本）：
        - 不使用分块并行（避免extraction_text类型错误）
        - 单线程处理（避免日志混乱）
        - 保留文本截断限制（避免超长文本导致超时）
        """
        quiet = (os.getenv("EXTRACTION_QUIET", "1").strip().lower() in {"1", "true", "yes", "on"})

        # 截断文本到max_length
        if len(text) > max_length:
            extraction_text = text[:max_length]
            if not quiet:
                logger.info(f"文本过长，截断至 {max_length} 字符（原长度: {len(text)}）")
        else:
            extraction_text = text

        api_key, base_url, model_id = self._model_config
        if not quiet:
            logger.info(f"开始知识提取: model={model_id}, text_length={len(extraction_text):,} chars")
            logger.info(f"  API: {base_url}")

        attempts = [
            {"force_json": False, "fence_output": True},
            {"force_json": True, "fence_output": False},
            {"force_json": True, "fence_output": True},
        ]

        last_err: Optional[Exception] = None
        for idx, cfg in enumerate(attempts, start=1):
            if not quiet:
                logger.info(f"尝试 {idx}/{len(attempts)}: force_json={cfg['force_json']}, fence_output={cfg['fence_output']}")
            model = self.model if not cfg["force_json"] else _build_openai_language_model(api_key, base_url, model_id, force_json=True)
            try:
                result = lx.extract(
                    text_or_documents=extraction_text,
                    prompt_description=self.prompt,
                    examples=self.examples,
                    model=model,
                    fence_output=cfg["fence_output"],
                    use_schema_constraints=False,
                    prompt_validation_level=PromptValidationLevel.OFF,
                    temperature=0,
                    max_workers=1,            # 单线程处理（避免extraction_text类型错误）
                    show_progress=True,
                )
                if not quiet:
                    logger.info(f"✓ 提取成功（尝试 {idx}）: 获得 {len(result.extractions)} 个提取结果")
                break
            except (KeyboardInterrupt, SystemExit):
                # Stop immediately on user/app interruption (Streamlit stop, Ctrl+C, etc.)
                logger.warning("检测到中断信号，停止知识提取重试")
                raise
            except Exception as e:
                last_err = e
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(f"✗ 提取失败（尝试 {idx}）: {error_type}: {error_msg}")

                # During interpreter shutdown, thread pools can't accept new tasks.
                # Retrying only makes it worse, so fail fast.
                if isinstance(e, RuntimeError) and "cannot schedule new futures after interpreter shutdown" in error_msg:
                    logger.error("解释器正在关闭，终止重试以避免 futures 提交失败")
                    raise

                # 记录详细的错误堆栈（仅在最后一次尝试时）
                if idx == len(attempts):
                    import traceback
                    logger.error(f"完整错误堆栈:\n{traceback.format_exc()}")

                # Small backoff to ride out transient empty responses / rate limits.
                if idx < len(attempts):
                    if not quiet:
                        logger.info(f"等待 1 秒后重试...")
                    time.sleep(1.0)
        else:
            assert last_err is not None
            if not quiet:
                logger.error(f"所有尝试均失败，抛出最后一个错误")
            raise last_err

        extractions: List[KnowledgeExtraction] = []
        # result itself is an AnnotatedDocument
        if not quiet:
            logger.info(f"开始处理 {len(result.extractions)} 个提取结果...")

        type_error_count = 0
        for idx, ext in enumerate(result.extractions):
            ext_text = ext.extraction_text

            # 检查并修复 extraction_text 类型问题
            if not isinstance(ext_text, (str, int, float)):
                type_error_count += 1
                original_type = type(ext_text).__name__
                logger.warning(
                    f"提取结果 #{idx+1} 的 extraction_text 类型错误: "
                    f"期望 str/int/float，实际为 {original_type}"
                )

                try:
                    import json
                    ext_text = json.dumps(ext_text, ensure_ascii=False)
                    logger.info(f"  → 已转换为 JSON 字符串: {ext_text[:100]}...")
                except Exception as e:
                    ext_text = str(ext_text)
                    logger.warning(f"  → JSON 转换失败，使用 str() 转换: {e}")

            char_interval = None
            if ext.char_interval:
                char_interval = {
                    "start_pos": ext.char_interval.start_pos,
                    "end_pos": ext.char_interval.end_pos
                }
            extractions.append(
                KnowledgeExtraction(
                    doc_id=self.doc_id,
                    doc_title=self.doc_title,
                    extraction_class=ext.extraction_class,
                    extraction_text=str(ext_text),
                    char_interval=char_interval,
                    attributes=ext.attributes,
                )
            )

        if type_error_count > 0:
            logger.warning(f"共发现 {type_error_count} 个类型错误的 extraction_text，已全部修复")

        if not quiet:
            logger.info(f"✓ 知识提取完成: 成功提取 {len(extractions)} 个知识点")
        return extractions


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
