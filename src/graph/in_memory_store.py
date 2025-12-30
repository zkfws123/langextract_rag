import json
from pathlib import Path
from typing import Dict, List, Optional

from src.graph.models import KnowledgeExtraction


class InMemoryGraphStore:
    def __init__(self, knowledge_graph: Optional[dict] = None):
        self.knowledge_graph = knowledge_graph or {"entities": {}, "relations": []}

    def build_from_extractions(self, extractions: List[KnowledgeExtraction]) -> None:
        for ext in extractions:
            if ext.extraction_class == "关系描述":
                attrs = ext.attributes
                self.knowledge_graph["relations"].append({
                    "text": ext.extraction_text,
                    "type": attrs.get("类型", "未知"),
                    "subject": attrs.get("主体1"),
                    "object": attrs.get("主体2"),
                    "relation": attrs.get("关系"),
                    "source": ext.doc_title,
                })
            elif ext.extraction_class in ["实体", "数据指标"]:
                entity_name = ext.extraction_text
                if entity_name not in self.knowledge_graph["entities"]:
                    self.knowledge_graph["entities"][entity_name] = {
                        "type": ext.extraction_class,
                        "attributes": ext.attributes,
                        "mentions": [],
                    }
                self.knowledge_graph["entities"][entity_name]["mentions"].append({
                    "source": ext.doc_title,
                    "position": ext.char_interval,
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
