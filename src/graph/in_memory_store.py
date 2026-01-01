import json
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

from src.graph.models import KnowledgeExtraction

if TYPE_CHECKING:
    from src.parsers.relation_extractor import RelationTriple


class InMemoryGraphStore:
    def __init__(self, knowledge_graph: Optional[dict] = None):
        self.knowledge_graph = knowledge_graph or {"entities": {}, "relations": []}

    def build_from_extractions(
        self, 
        extractions: List[KnowledgeExtraction],
        stage2_relations: Optional[List["RelationTriple"]] = None
    ) -> None:
        """
        从知识点构建图谱
        
        Args:
            extractions: 第一阶段提取的知识点
            stage2_relations: 第二阶段抽取的关系三元组（可选）
        """
        def _ensure_entity(name: str, entity_type: str, attrs: dict) -> None:
            if not name:
                return
            if name not in self.knowledge_graph["entities"]:
                self.knowledge_graph["entities"][name] = {
                    "type": entity_type,
                    "attributes": attrs or {},
                    "mentions": [],
                }
            else:
                # Merge attributes shallowly (keep existing keys unless new)
                existing_attrs = self.knowledge_graph["entities"][name].get("attributes") or {}
                merged = dict(existing_attrs)
                for k, v in (attrs or {}).items():
                    if k not in merged:
                        merged[k] = v
                self.knowledge_graph["entities"][name]["attributes"] = merged

        def _add_mention(name: str, ext: KnowledgeExtraction) -> None:
            if not name:
                return
            self.knowledge_graph["entities"][name]["mentions"].append({
                "source": ext.doc_title,
                "position": ext.char_interval,
            })

        def _add_relation(subject: str, obj: str, rel_type: str, ext: KnowledgeExtraction, relation_label: Optional[str] = None) -> None:
            if not subject or not obj:
                return
            self.knowledge_graph["relations"].append({
                "text": ext.extraction_text,
                "type": rel_type or "未知",
                "subject": subject,
                "object": obj,
                "relation": relation_label or rel_type or "关联",
                "source": ext.doc_title,
            })

        for ext in extractions:
            cls = ext.extraction_class
            attrs = ext.attributes or {}

            # 1) Original relation format (general config)
            if cls == "关系描述":
                _add_relation(
                    attrs.get("主体1"),
                    attrs.get("主体2"),
                    attrs.get("类型", "未知"),
                    ext,
                    relation_label=attrs.get("关系"),
                )
                # Also ensure endpoints exist
                _ensure_entity(attrs.get("主体1") or "", "实体", {})
                _ensure_entity(attrs.get("主体2") or "", "实体", {})
                continue

            # 2) Ziwei: 宫位关系网络 => edges between 宫位组 items
            if cls == "宫位关系网络":
                palace_group = attrs.get("宫位组")
                rel_type = attrs.get("关系类型") or attrs.get("原则") or cls

                if isinstance(palace_group, list) and len(palace_group) >= 2:
                    # Ensure nodes + connect consecutive pairs
                    cleaned = [str(x).strip() for x in palace_group if str(x).strip()]
                    for name in cleaned:
                        _ensure_entity(name, "宫位", {"来源": "宫位关系网络"})
                    for i in range(len(cleaned) - 1):
                        _add_relation(cleaned[i], cleaned[i + 1], rel_type, ext)
                    continue

            # 3) Entities (general config)
            if cls in ["实体", "数据指标"]:
                entity_name = ext.extraction_text
                _ensure_entity(entity_name, cls, attrs)
                _add_mention(entity_name, ext)
                continue

            # 4) Default: treat other extraction classes as entity-like nodes
            entity_name = ext.extraction_text
            _ensure_entity(entity_name, cls or "实体", attrs)
            _add_mention(entity_name, ext)
        
        # 5) Add stage2 relations (from RelationExtractor)
        if stage2_relations:
            for rel_triple in stage2_relations:
                # Ensure both nodes exist (they should already from stage1)
                _ensure_entity(rel_triple.subject_id, "实体", {})
                _ensure_entity(rel_triple.object_id, "实体", {})
                
                # Add edge
                self.knowledge_graph["relations"].append({
                    "text": f"{rel_triple.subject_id} - {rel_triple.object_id}",
                    "type": rel_triple.relation,
                    "subject": rel_triple.subject_id,
                    "object": rel_triple.object_id,
                    "relation": rel_triple.relation,
                    "source": "二阶段关系抽取",
                    "confidence": rel_triple.confidence,
                    "metadata": rel_triple.metadata or {}
                })

    def save(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.knowledge_graph, f, ensure_ascii=False, indent=2)

    def load(self, input_path: Path) -> None:
        with open(input_path, "r", encoding="utf-8") as f:
            self.knowledge_graph = json.load(f)

    def search(self, query_entity: str, hop: int = 1) -> Dict:
        results = {
            "matched_entities": [],
            "related_relations": [],
            "connected_entities": set(),
        }
        matched = []
        for entity_name, entity_data in self.knowledge_graph.get("entities", {}).items():
            if query_entity in entity_name:
                matched.append((entity_name, entity_data))
        results["matched_entities"] = matched

        if hop >= 1:
            for relation in self.knowledge_graph.get("relations", []):
                subj = relation.get("subject")
                obj = relation.get("object")
                if not subj or not obj:
                    continue
                if any(query_entity in x for x in [subj, obj]):
                    results["related_relations"].append(relation)
                    results["connected_entities"].add(subj)
                    results["connected_entities"].add(obj)
                if hop >= 2 and matched:
                    for name, _ in matched:
                        if name == subj or name == obj:
                            results["related_relations"].append(relation)
                            results["connected_entities"].add(subj)
                            results["connected_entities"].add(obj)
        results["connected_entities"] = list(results["connected_entities"])
        return results
