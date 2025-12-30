from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class KnowledgeExtraction:
    doc_id: str
    doc_title: str
    extraction_class: str
    extraction_text: str
    char_interval: Optional[dict] = None
    attributes: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_searchable_text(self) -> str:
        parts = [
            f"类型: {self.extraction_class}",
            f"内容: {self.extraction_text}",
            f"来源: {self.doc_title}",
        ]
        if self.attributes:
            for k, v in self.attributes.items():
                parts.append(f"{k}: {v}")
        return " | ".join(parts)
