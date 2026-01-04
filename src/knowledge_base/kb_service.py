"""知识库服务层 - 负责知识库的CRUD和文档管理"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.knowledge_base.models import (
    KnowledgeBase, 
    Document, 
    KBConfig,
    KBStatus, 
    DocumentStatus
)

# 知识库存储根目录
_KB_ROOT = Path(__file__).resolve().parents[2] / "outputs" / "knowledge_bases"


class KnowledgeBaseService:
    """知识库服务 - 管理知识库的创建、删除、文档处理"""
    
    def __init__(self, root: Optional[Path] = None):
        self.root = root or _KB_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
    
    # ========== 知识库 CRUD ==========
    
    def create_kb(self, name: str, description: str = "", **config_kwargs) -> KnowledgeBase:
        """创建新知识库"""
        kb = KnowledgeBase.create(name, description, **config_kwargs)
        kb_dir = self._kb_dir(kb.id)
        kb_dir.mkdir(parents=True, exist_ok=True)
        (kb_dir / "documents").mkdir(exist_ok=True)
        
        # 初始化空图谱
        self._save_graph(kb.id, {"entities": {}, "relations": []})
        self._save_kb_config(kb)
        return kb
    
    def get_kb(self, kb_id: str) -> Optional[KnowledgeBase]:
        """获取知识库"""
        config_path = self._kb_dir(kb_id) / "config.json"
        if not config_path.exists():
            return None
        return KnowledgeBase.from_dict(
            json.loads(config_path.read_text(encoding="utf-8"))
        )
    
    def list_kbs(self) -> List[KnowledgeBase]:
        """列出所有知识库"""
        kbs = []
        if not self.root.exists():
            return kbs
        for subdir in self.root.iterdir():
            if subdir.is_dir():
                kb = self.get_kb(subdir.name)
                if kb:
                    kbs.append(kb)
        return sorted(kbs, key=lambda x: x.created_at, reverse=True)
    
    def update_kb(self, kb: KnowledgeBase) -> None:
        """更新知识库配置"""
        kb.updated_at = datetime.now()
        self._save_kb_config(kb)
    
    def delete_kb(self, kb_id: str) -> bool:
        """删除知识库（包括所有文档和图谱）"""
        kb_dir = self._kb_dir(kb_id)
        if kb_dir.exists():
            shutil.rmtree(kb_dir, ignore_errors=True)
            return True
        return False
    
    # ========== 文档管理 ==========
    
    def add_document(self, kb_id: str, filename: str, content: bytes) -> Document:
        """添加文档到知识库"""
        doc = Document.create(filename, kb_id)
        doc_dir = self._doc_dir(kb_id, doc.id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存原始文件
        (doc_dir / filename).write_bytes(content)
        self._save_doc_meta(doc)
        
        # 更新知识库文档数量
        kb = self.get_kb(kb_id)
        if kb:
            kb.document_count += 1
            self.update_kb(kb)
        
        return doc
    
    def get_document(self, kb_id: str, doc_id: str) -> Optional[Document]:
        """获取文档"""
        meta_path = self._doc_dir(kb_id, doc_id) / "meta.json"
        if not meta_path.exists():
            return None
        return Document.from_dict(
            json.loads(meta_path.read_text(encoding="utf-8"))
        )
    
    def list_documents(self, kb_id: str) -> List[Document]:
        """列出知识库中的所有文档"""
        docs = []
        docs_dir = self._kb_dir(kb_id) / "documents"
        if not docs_dir.exists():
            return docs
        for subdir in docs_dir.iterdir():
            if subdir.is_dir():
                doc = self.get_document(kb_id, subdir.name)
                if doc:
                    docs.append(doc)
        return sorted(docs, key=lambda x: x.created_at, reverse=True)
    
    def update_document(self, doc: Document) -> None:
        """更新文档状态"""
        doc.updated_at = datetime.now()
        self._save_doc_meta(doc)
    
    def delete_document(self, kb_id: str, doc_id: str) -> bool:
        """删除文档"""
        # Capture filename before deletion (needed for graph/source cleanup).
        doc = self.get_document(kb_id, doc_id)
        doc_title = doc.filename if doc else ""

        doc_dir = self._doc_dir(kb_id, doc_id)
        if not doc_dir.exists():
            return False

        # 1) Delete document files
        shutil.rmtree(doc_dir, ignore_errors=True)

        # 2) Best-effort: delete vectors from Chroma collection for this document
        try:
            from src.retrieval.vector.chroma_store import ChromaVectorStore

            collection_name = self.get_collection_name(kb_id)
            vector_store = ChromaVectorStore(collection_name=collection_name)
            # LangChain Chroma exposes underlying chromadb collection via _collection
            # We filter by metadata field "doc_id" which we set during indexing.
            vector_store.vectorstore._collection.delete(where={"doc_id": doc_id})
        except Exception:
            # Don't block deletion if vector store cleanup fails.
            pass

        # 3) Best-effort: remove mentions/source in graph.json
        try:
            graph = self.get_graph(kb_id)
            entities = graph.get("entities", {}) or {}

            for _name, data in entities.items():
                mentions = data.get("mentions")
                if isinstance(mentions, list) and mentions:
                    data["mentions"] = [
                        m
                        for m in mentions
                        if (m.get("source") != doc_title and m.get("source") != doc_id)
                    ]

            relations = graph.get("relations", []) or []
            if isinstance(relations, list) and relations:
                graph["relations"] = [
                    r
                    for r in relations
                    if (r.get("source") != doc_title and r.get("source") != doc_id)
                ]

            self.save_graph(kb_id, graph)
        except Exception:
            pass

        # 4) Update knowledge base doc count
        kb = self.get_kb(kb_id)
        if kb and kb.document_count > 0:
            kb.document_count -= 1
            self.update_kb(kb)

        return True
    
    def get_document_content(self, kb_id: str, doc_id: str) -> Optional[bytes]:
        """获取文档原始内容"""
        doc = self.get_document(kb_id, doc_id)
        if not doc:
            return None
        file_path = self._doc_dir(kb_id, doc_id) / doc.filename
        if file_path.exists():
            return file_path.read_bytes()
        return None
    
    # ========== 图谱管理 ==========
    
    def get_graph(self, kb_id: str) -> Dict[str, Any]:
        """获取知识库的图谱"""
        graph_path = self._kb_dir(kb_id) / "graph.json"
        if graph_path.exists():
            return json.loads(graph_path.read_text(encoding="utf-8"))
        return {"entities": {}, "relations": []}
    
    def save_graph(self, kb_id: str, graph: Dict[str, Any]) -> None:
        """保存知识库图谱"""
        self._save_graph(kb_id, graph)
        
        # 更新统计
        kb = self.get_kb(kb_id)
        if kb:
            kb.total_entities = len(graph.get("entities", {}))
            kb.total_relations = len(graph.get("relations", []))
            kb.status = KBStatus.READY if kb.total_entities > 0 else KBStatus.EMPTY
            self.update_kb(kb)
    
    def merge_graph(self, kb_id: str, new_graph: Dict[str, Any]) -> Dict[str, Any]:
        """合并新图谱到现有图谱（增量更新）"""
        existing = self.get_graph(kb_id)

        # 合并实体
        for name, entity_data in new_graph.get("entities", {}).items():
            if name not in existing["entities"]:
                existing["entities"][name] = entity_data
            else:
                # 合并属性和mentions
                old_attrs = existing["entities"][name].get("attributes", {})
                new_attrs = entity_data.get("attributes", {})
                merged_attrs = {**old_attrs, **new_attrs}
                existing["entities"][name]["attributes"] = merged_attrs

                old_mentions = existing["entities"][name].get("mentions", [])
                new_mentions = entity_data.get("mentions", [])
                existing["entities"][name]["mentions"] = old_mentions + new_mentions

        # 合并关系（去重）
        existing_rel_keys = set()
        for rel in existing.get("relations", []):
            key = (rel.get("subject"), rel.get("object"), rel.get("relation"))
            existing_rel_keys.add(key)

        for rel in new_graph.get("relations", []):
            key = (rel.get("subject"), rel.get("object"), rel.get("relation"))
            if key not in existing_rel_keys:
                existing["relations"].append(rel)
                existing_rel_keys.add(key)

        self.save_graph(kb_id, existing)
        return existing

    def clear_graph(self, kb_id: str) -> None:
        """清空知识库的知识图谱（保留文档）"""
        # 重置为空图谱
        empty_graph = {"entities": {}, "relations": []}
        self.save_graph(kb_id, empty_graph)

        # 更新知识库状态
        kb = self.get_kb(kb_id)
        if kb:
            kb.total_entities = 0
            kb.total_relations = 0
            kb.status = KBStatus.EMPTY
            self.update_kb(kb)
    
    # ========== 文档处理缓存 ==========
    
    def save_doc_extractions(self, kb_id: str, doc_id: str, extractions: List[dict]) -> None:
        """保存文档提取结果"""
        doc_dir = self._doc_dir(kb_id, doc_id)
        (doc_dir / "extractions.json").write_text(
            json.dumps(extractions, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    def load_doc_extractions(self, kb_id: str, doc_id: str) -> Optional[List[dict]]:
        """加载文档提取结果"""
        path = self._doc_dir(kb_id, doc_id) / "extractions.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None
    
    def save_doc_markdown(self, kb_id: str, doc_id: str, markdown: str, pages: List[str] = None) -> None:
        """保存文档Markdown"""
        doc_dir = self._doc_dir(kb_id, doc_id)
        (doc_dir / "content.md").write_text(markdown, encoding="utf-8")
        if pages:
            (doc_dir / "pages.json").write_text(
                json.dumps(pages, ensure_ascii=False),
                encoding="utf-8"
            )
    
    def load_doc_markdown(self, kb_id: str, doc_id: str) -> Optional[str]:
        """加载文档Markdown"""
        path = self._doc_dir(kb_id, doc_id) / "content.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None

    def load_doc_pages(self, kb_id: str, doc_id: str) -> Optional[List[str]]:
        """加载文档分页 Markdown（pages.json）"""
        path = self._doc_dir(kb_id, doc_id) / "pages.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None
    
    # ========== 向量库 Collection 名称 ==========
    
    def get_collection_name(self, kb_id: str) -> str:
        """获取知识库对应的ChromaDB collection名称"""
        return f"kb_{kb_id}"
    
    # ========== 私有方法 ==========
    
    def _kb_dir(self, kb_id: str) -> Path:
        return self.root / kb_id
    
    def _doc_dir(self, kb_id: str, doc_id: str) -> Path:
        return self._kb_dir(kb_id) / "documents" / doc_id
    
    def _save_kb_config(self, kb: KnowledgeBase) -> None:
        config_path = self._kb_dir(kb.id) / "config.json"
        config_path.write_text(
            json.dumps(kb.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    def _save_doc_meta(self, doc: Document) -> None:
        meta_path = self._doc_dir(doc.kb_id, doc.id) / "meta.json"
        meta_path.write_text(
            json.dumps(doc.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    
    def _save_graph(self, kb_id: str, graph: Dict[str, Any]) -> None:
        graph_path = self._kb_dir(kb_id) / "graph.json"
        graph_path.write_text(
            json.dumps(graph, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


# 全局单例
_service_instance: Optional[KnowledgeBaseService] = None

def get_kb_service() -> KnowledgeBaseService:
    """获取知识库服务单例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = KnowledgeBaseService()
    return _service_instance
