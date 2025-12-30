import json
import os
import uuid
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import chromadb

from src.graph.models import KnowledgeExtraction

load_dotenv()

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db_chapter5")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "pdf_knowledge_graph")


class ChromaVectorStore:
    def __init__(self,
                 persist_dir: Optional[str] = None,
                 collection_name: Optional[str] = None):
        self.persist_dir = Path(persist_dir or CHROMA_PERSIST_DIR)
        self.collection_name = collection_name or COLLECTION_NAME
        self.embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
            check_embedding_ctx_length=False,
            chunk_size=10,
        )
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._reset_collection()

    def _reset_collection(self) -> None:
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            client=self.client,
        )

    def index_extractions(self, extractions: List[KnowledgeExtraction]) -> None:
        if not extractions:
            return
        texts = [ext.to_searchable_text() for ext in extractions]
        metadatas = []
        ids = []
        for ext in extractions:
            ids.append(str(uuid.uuid4()))
            metadatas.append({
                "doc_id": ext.doc_id,
                "doc_title": ext.doc_title,
                "extraction_class": ext.extraction_class,
                "extraction_text": ext.extraction_text,
                "char_interval": json.dumps(ext.char_interval) if ext.char_interval else "",
                "attributes": json.dumps(ext.attributes, ensure_ascii=False),
            })
        self.vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def similarity_search(self, query: str, top_k: int = 5):
        results = self.vectorstore.similarity_search_with_score(query, k=top_k)
        formatted = []
        for doc, score in results:
            char_interval_str = doc.metadata.get("char_interval", "")
            char_interval = json.loads(char_interval_str) if char_interval_str else None
            attributes_str = doc.metadata.get("attributes", "{}")
            try:
                attributes = json.loads(attributes_str)
            except Exception:
                attributes = {}
            formatted.append({
                "score": 1 / (1 + score),
                "doc_id": doc.metadata.get("doc_id"),
                "doc_title": doc.metadata.get("doc_title"),
                "extraction_class": doc.metadata.get("extraction_class"),
                "extraction_text": doc.metadata.get("extraction_text"),
                "char_interval": char_interval,
                "attributes": attributes,
                "content": doc.page_content,
            })
        return formatted
