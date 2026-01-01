"""二阶段关系抽取器 - 从已提取的知识点中识别关系"""
import os
import re
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI

from src.graph.models import KnowledgeExtraction
from src.configs.prompts.relation_extraction import PROMPT, EXAMPLES, RELATION_TYPES

load_dotenv(override=True)


def _strip_markdown_fence(text: str) -> str:
    """Strip markdown code fence markers (```json ... ```) from model responses."""
    if not text:
        return text
    text = text.strip()
    pattern = r'^```(?:json|JSON)?\s*\n?(.*?)\n?```$'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


# 优先使用 Gemini 配置
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "deepseek-chat")


@dataclass
class RelationTriple:
    """关系三元组"""
    subject_id: str  # 主体知识点的extraction_text（用于图谱匹配）
    relation: str    # 关系类型
    object_id: str   # 客体知识点的extraction_text
    confidence: float = 1.0  # 置信度（可选）
    metadata: Dict[str, Any] = None  # 额外元数据

    def to_dict(self) -> dict:
        return {
            "subject": self.subject_id,
            "relation": self.relation,
            "object": self.object_id,
            "confidence": self.confidence,
            "metadata": self.metadata or {}
        }


class RelationExtractor:
    """二阶段关系抽取器"""
    
    def __init__(self, model: Optional[str] = None, chunk_size: int = 20):
        """
        Args:
            model: 模型名称（默认使用GEMINI_MODEL或DEFAULT_MODEL）
            chunk_size: 单次抽取的最大知识点数量（避免context过长，减少到20）
        """
        api_key = GEMINI_API_KEY or DEEPSEEK_API_KEY
        base_url = GEMINI_BASE_URL or DEEPSEEK_BASE_URL
        model_id = model or GEMINI_MODEL or DEFAULT_MODEL
        
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model_id
        self.chunk_size = chunk_size
        
    def extract_relations(
        self,
        extractions: List[KnowledgeExtraction],
        source_text: str,
        max_text_length: int = 8000
    ) -> List[RelationTriple]:
        """
        从已提取的知识点中识别关系
        
        Args:
            extractions: 第一阶段提取的知识点列表
            source_text: 原始文本（用于上下文理解）
            max_text_length: 最大文本长度（避免超token）
        
        Returns:
            关系三元组列表
        """
        if not extractions:
            return []
        
        # 截断过长的文本
        text_context = source_text[:max_text_length]
        if len(source_text) > max_text_length:
            text_context += "\n... (文本已截断)"
        
        # 构建知识点索引（临时编号 -> extraction_text）
        extraction_map = {}
        extraction_list = []
        for idx, ext in enumerate(extractions, start=1):
            extraction_map[idx] = ext.extraction_text
            extraction_list.append({
                "id": idx,
                "class": ext.extraction_class,
                "text": ext.extraction_text[:200],  # 截断过长的text
                "attributes": ext.attributes
            })
        
        # 分块处理（大文档可能有几百个知识点）
        all_relations = []
        total_chunks = (len(extraction_list) + self.chunk_size - 1) // self.chunk_size
        
        for i in range(0, len(extraction_list), self.chunk_size):
            chunk_idx = i // self.chunk_size + 1
            print(f"  处理分块 {chunk_idx}/{total_chunks}...")
            
            chunk = extraction_list[i:i + self.chunk_size]
            chunk_relations = self._extract_chunk_relations(
                text_context, chunk, extraction_map
            )
            all_relations.extend(chunk_relations)
            print(f"    本块发现 {len(chunk_relations)} 条关系")
        
        return all_relations
    
    def _extract_chunk_relations(
        self,
        text_context: str,
        extraction_chunk: List[Dict],
        extraction_map: Dict[int, str]
    ) -> List[RelationTriple]:
        """处理单个chunk的关系抽取"""
        
        # 构建用户消息
        user_message = self._build_user_message(text_context, extraction_chunk)
        
        # 调用LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},  # 强制JSON输出
                timeout=60.0  # 增加超时时间
            )
            
            content = response.choices[0].message.content
            
            # 处理markdown fence包裹的JSON
            content = _strip_markdown_fence(content)
            
            # 尝试解析JSON
            relations_data = json.loads(content)
            
            # 兼容两种格式：{"relations": [...]} 或直接 [...]
            if isinstance(relations_data, list):
                relations_list = relations_data
            else:
                relations_list = relations_data.get("relations", [])
            
            # 解析为RelationTriple对象
            relations = []
            for rel in relations_list:
                subject_idx = rel.get("subject_id")
                object_idx = rel.get("object_id")
                relation_type = rel.get("relation")
                
                # 验证索引有效性
                if subject_idx not in extraction_map or object_idx not in extraction_map:
                    continue
                
                # 验证关系类型
                if relation_type not in RELATION_TYPES:
                    continue
                
                relations.append(RelationTriple(
                    subject_id=extraction_map[subject_idx],
                    relation=relation_type,
                    object_id=extraction_map[object_idx],
                    confidence=rel.get("confidence", 1.0),
                    metadata={"reason": rel.get("reason", "")}
                ))
            
            return relations
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON解析失败: {e}")
            print(f"   LLM返回内容: {content[:200]}...")
            return []
        except Exception as e:
            import traceback
            print(f"⚠️  关系抽取失败: {e}")
            print(f"   使用模型: {self.model}")
            print(f"   错误详情: {traceback.format_exc()}")
            return []
    
    def _build_user_message(self, text_context: str, extraction_chunk: List[Dict]) -> str:
        """构建用户消息"""
        # 限制原文长度（太长会导致超token）
        max_text_len = 3000
        if len(text_context) > max_text_len:
            text_context = text_context[:max_text_len] + "\n... (为避免超长已截断)"
        
        msg_parts = [
            "【原始文本】",
            text_context,
            "",
            "【已提取的知识点】",
        ]
        
        for ext in extraction_chunk:
            msg_parts.append(
                f"#{ext['id']} | {ext['class']} | {ext['text']}"
            )
        
        msg_parts.extend([
            "",
            "【任务】",
            "请识别上述知识点之间的语义关系，输出JSON格式：",
            '{"relations": [{"subject_id": 1, "relation": "术语引用", "object_id": 3, "reason": "..."}]}'
        ])
        
        return "\n".join(msg_parts)


def batch_extract_relations(
    extractions: List[KnowledgeExtraction],
    source_text: str,
    extractor: Optional[RelationExtractor] = None
) -> List[RelationTriple]:
    """
    便捷函数：批量抽取关系
    
    Args:
        extractions: 知识点列表
        source_text: 原始文本
        extractor: 可选的extractor实例（复用连接）
    
    Returns:
        关系三元组列表
    """
    if extractor is None:
        extractor = RelationExtractor()
    
    return extractor.extract_relations(extractions, source_text)
