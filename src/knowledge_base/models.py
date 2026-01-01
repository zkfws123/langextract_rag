"""知识库数据模型"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import uuid


class KBStatus(Enum):
    """知识库状态"""
    EMPTY = "empty"          # 刚创建，无文档
    PROCESSING = "processing" # 处理中
    READY = "ready"          # 就绪可用
    ERROR = "error"          # 出错


class DocumentStatus(Enum):
    """文档状态"""
    PENDING = "pending"      # 待处理
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"  # 完成
    ERROR = "error"          # 出错


@dataclass
class Document:
    """文档记录"""
    id: str
    filename: str
    kb_id: str
    status: DocumentStatus = DocumentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    entity_count: int = 0
    relation_count: int = 0
    chunk_count: int = 0
    error_message: Optional[str] = None
    
    @classmethod
    def create(cls, filename: str, kb_id: str) -> "Document":
        """创建新文档记录"""
        return cls(
            id=str(uuid.uuid4())[:8],
            filename=filename,
            kb_id=kb_id,
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "kb_id": self.kb_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "chunk_count": self.chunk_count,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        return cls(
            id=data["id"],
            filename=data["filename"],
            kb_id=data["kb_id"],
            status=DocumentStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            entity_count=data.get("entity_count", 0),
            relation_count=data.get("relation_count", 0),
            chunk_count=data.get("chunk_count", 0),
            error_message=data.get("error_message"),
        )


@dataclass
class KBConfig:
    """知识库配置"""
    description: str = ""
    llm_model: str = "gpt-5.2-high"    # 默认使用 gpt-5.2-high
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 2000
    chunk_overlap: int = 200
    extraction_prompt: str = "general"  # 提取配置模板
    
    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "llm_model": self.llm_model,
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "extraction_prompt": self.extraction_prompt,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "KBConfig":
        return cls(**data)


@dataclass
class KnowledgeBase:
    """知识库"""
    id: str
    name: str
    status: KBStatus = KBStatus.EMPTY
    config: KBConfig = field(default_factory=KBConfig)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    document_count: int = 0
    total_entities: int = 0
    total_relations: int = 0
    
    @classmethod
    def create(cls, name: str, description: str = "", **config_kwargs) -> "KnowledgeBase":
        """创建新知识库"""
        config = KBConfig(description=description, **config_kwargs)
        return cls(
            id=str(uuid.uuid4())[:8],
            name=name,
            config=config,
        )
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "config": self.config.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "document_count": self.document_count,
            "total_entities": self.total_entities,
            "total_relations": self.total_relations,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeBase":
        return cls(
            id=data["id"],
            name=data["name"],
            status=KBStatus(data["status"]),
            config=KBConfig.from_dict(data["config"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            document_count=data.get("document_count", 0),
            total_entities=data.get("total_entities", 0),
            total_relations=data.get("total_relations", 0),
        )
