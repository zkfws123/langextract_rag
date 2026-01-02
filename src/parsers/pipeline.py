"""知识提取流水线 - 统一管理实体提取和关系抽取"""
import logging
import os
from typing import List, Tuple, Optional
from src.graph.models import KnowledgeExtraction
from src.parsers.knowledge_extractor import KnowledgeExtractor
from src.parsers.relation_extractor import RelationExtractor, RelationTriple

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
        quiet = (os.getenv("EXTRACTION_QUIET", "1").strip().lower() in {"1", "true", "yes", "on"})
        if not quiet:
            logger.info(f"=" * 60)
            logger.info(f"开始知识提取流水线: doc_id={self.doc_id}, doc_title={self.doc_title}")
            logger.info(f"=" * 60)

        # 第一阶段：提取实体
        if not quiet:
            logger.info("【阶段 1/2】开始提取实体...")
        try:
            extractions = self.entity_extractor.extract_from_text(text, max_length)
            if not quiet:
                logger.info(f"【阶段 1/2】完成: 提取了 {len(extractions)} 个实体")
        except Exception as e:
            logger.error(f"【阶段 1/2】失败: {type(e).__name__}: {e}")
            raise

        # 第二阶段：提取关系
        relations = []
        if self.enable_relation_extraction and self.relation_extractor and extractions:
            if not quiet:
                logger.info("【阶段 2/2】开始提取实体间关系...")
            try:
                relations = self.relation_extractor.extract_relations(extractions, text)
                if not quiet:
                    logger.info(f"【阶段 2/2】完成: 发现 {len(relations)} 条关系")
            except Exception as e:
                logger.error(f"【阶段 2/2】失败: {type(e).__name__}: {e}")
                # 关系提取失败不影响整体流程，继续返回实体
                logger.warning("关系提取失败，但实体提取成功，继续执行...")
        else:
            if not self.enable_relation_extraction:
                logger.info("【阶段 2/2】跳过: 关系提取已禁用")
            elif not extractions:
                logger.info("【阶段 2/2】跳过: 没有提取到实体")

        if not quiet:
            logger.info(f"=" * 60)
            logger.info(f"知识提取流水线完成: {len(extractions)} 个实体, {len(relations)} 条关系")
            logger.info(f"=" * 60)

        return extractions, relations
