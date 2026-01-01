"""知识提取流水线 - 统一管理实体提取和关系抽取"""
from typing import List, Tuple, Optional
from src.graph.models import KnowledgeExtraction
from src.parsers.knowledge_extractor import KnowledgeExtractor
from src.parsers.relation_extractor import RelationExtractor, RelationTriple


class KnowledgeExtractionPipeline:
    """
    知识提取流水线：
    1. 第一阶段：提取实体和数据指标
    2. 第二阶段：从实体中识别关系
    """
    
    def __init__(
        self, 
        doc_id: str,
        doc_title: Optional[str] = None,
        enable_relation_extraction: bool = True,
        custom_prompt: Optional[str] = None,
        custom_examples: Optional[list] = None
    ):
        """
        Args:
            doc_id: 文档ID
            doc_title: 文档标题
            enable_relation_extraction: 是否启用二阶段关系抽取
            custom_prompt: 自定义提示词
            custom_examples: 自定义示例
        """
        self.doc_id = doc_id
        self.doc_title = doc_title or doc_id
        self.enable_relation_extraction = enable_relation_extraction
        
        # 第一阶段：实体提取器
        self.entity_extractor = KnowledgeExtractor(
            doc_id=doc_id,
            doc_title=doc_title,
            custom_prompt=custom_prompt,
            custom_examples=custom_examples
        )
        
        # 第二阶段：关系提取器
        self.relation_extractor = RelationExtractor() if enable_relation_extraction else None
    
    def extract(
        self, 
        text: str, 
        max_length: int = 8000
    ) -> Tuple[List[KnowledgeExtraction], List[RelationTriple]]:
        """
        执行完整的知识提取流水线
        
        Args:
            text: 待提取的文本
            max_length: 最大文本长度
            
        Returns:
            (实体列表, 关系列表)
        """
        # 第一阶段：提取实体
        extractions = self.entity_extractor.extract_from_text(text, max_length)
        
        # 第二阶段：提取关系
        relations = []
        if self.enable_relation_extraction and self.relation_extractor and extractions:
            print("\n正在提取实体间关系...")
            relations = self.relation_extractor.extract_relations(extractions, text)
            print(f"发现 {len(relations)} 条关系\n")
        
        return extractions, relations
