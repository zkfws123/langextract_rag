import os
import textwrap
from pathlib import Path
from typing import List, Optional

import langextract as lx
from dotenv import load_dotenv
from langextract.providers.openai import OpenAILanguageModel
from langextract.prompt_validation import PromptValidationLevel

from src.graph.models import KnowledgeExtraction
from src.graph.in_memory_store import InMemoryGraphStore
from src.retrieval.vector.chroma_store import ChromaVectorStore

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek-chat")


class KnowledgeExtractor:
    """
    LangExtract-powered knowledge extractor with precise char_interval traceability.
    Extracts entities, data metrics, relations, and events from text using LLM.
    """

    def __init__(self, doc_id: str, doc_title: Optional[str] = None):
        self.doc_id = doc_id
        self.doc_title = doc_title or doc_id
        self.model = OpenAILanguageModel(
            model_id=DEFAULT_MODEL,
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
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
            """)
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
        """Extract knowledge using LangExtract with full char_interval traceability."""
        if len(text) > max_length:
            extraction_text = text[:max_length]
        else:
            extraction_text = text

        result = lx.extract(
            text_or_documents=extraction_text,
            prompt_description=self.prompt,
            examples=self.examples,
            model=self.model,
            fence_output=True,
            use_schema_constraints=False,
            prompt_validation_level=PromptValidationLevel.OFF,
            show_progress=True,
        )

        extractions: List[KnowledgeExtraction] = []
        # result itself is an AnnotatedDocument
        for ext in result.extractions:
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
                    extraction_text=ext.extraction_text,
                    char_interval=char_interval,
                    attributes=ext.attributes,
                )
            )
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
