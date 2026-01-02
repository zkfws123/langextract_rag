"""测试 Notebook 复杂模式 - 完全复制 Notebook 的成功配置"""
import os
import sys
import json
import logging
import textwrap
from pathlib import Path
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv(override=True)

# 导入必要的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import langextract as lx
from langextract.providers.openai import OpenAILanguageModel
from langextract.prompt_validation import PromptValidationLevel

# 读取文档内容
markdown_path = Path("outputs/runs/7423da43f5cb/markdown_full.md")

if not markdown_path.exists():
    logger.error(f"❌ 文档不存在: {markdown_path}")
    sys.exit(1)

text = markdown_path.read_text(encoding="utf-8")
logger.info(f"✅ 读取文档成功: {len(text)} 字符")

# 截取前 2000 字符进行快速测试
test_text = text[:2000]
logger.info(f"📝 测试文本长度: {len(test_text)} 字符")

# 配置 API - 使用 Sonetto gpt-5.2-high
api_key = os.getenv("SONETTO_API_KEY")
base_url = os.getenv("SONETTO_BASE_URL")
model_id = os.getenv("SONETTO_MODEL_HIGH", "gpt-5.2-high")

logger.info(f"🔧 API 配置:")
logger.info(f"   Base URL: {base_url}")
logger.info(f"   Model: {model_id}")
logger.info(f"   API Key: {api_key[:20]}..." if api_key else "   API Key: None")

# 创建模型
model = OpenAILanguageModel(
    model_id=model_id,
    api_key=api_key,
    base_url=base_url
)

# ============================================
# 完全复制 Notebook 的配置（4000-4120行）
# ============================================
logger.info("\n" + "="*60)
logger.info("测试: 完全复制 Notebook 的复杂模式配置")
logger.info("="*60)

# Prompt - 完全复制 Notebook (4005-4018行)
extraction_prompt = textwrap.dedent("""\
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

# Few-shot 示例 - 完全复制 Notebook (4069-4107行)
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

examples = [
    lx.data.ExampleData(
        text=example_text,
        extractions=example_extractions
    )
]

logger.info(f"✅ Prompt 和示例配置完成")
logger.info(f"   示例文本长度: {len(example_text)} 字符")
logger.info(f"   示例提取数量: {len(example_extractions)} 个")

# 执行提取 - 完全复制 Notebook (4242-4251行)
try:
    logger.info("📡 调用 LangExtract API...")
    import time
    start_time = time.time()

    result = lx.extract(
        text_or_documents=test_text,
        prompt_description=extraction_prompt,
        examples=examples,
        model=model,
        fence_output=True,  # 要求 LLM 输出用代码块包裹，避免格式错误
        use_schema_constraints=False,  # 不使用严格的 schema 约束，提高灵活性
        prompt_validation_level=PromptValidationLevel.OFF,  # 关闭提示词验证
        show_progress=True,  # 显示提取进度
    )

    elapsed_time = time.time() - start_time
    logger.info(f"✅ 提取成功！耗时 {elapsed_time:.2f} 秒")
    logger.info(f"   提取了 {len(result.extractions)} 个知识点")

    # 显示前10个提取结果（包括错误的）
    logger.info(f"\n前10个提取结果:")
    for i, ext in enumerate(result.extractions[:10], 1):
        logger.info(f"   [{i}] 类别={ext.extraction_class}, 文本={ext.extraction_text[:60]}...")
        if ext.attributes:
            logger.info(f"       属性: {ext.attributes}")

    # 专门查看 extraction_class 为 "extraction_text" 的错误案例
    logger.info(f"\n错误案例（extraction_class='extraction_text'）:")
    error_cases = [ext for ext in result.extractions if ext.extraction_class == "extraction_text"]
    for i, ext in enumerate(error_cases[:5], 1):
        logger.info(f"   [{i}] 文本={ext.extraction_text[:80]}...")
        if ext.attributes:
            logger.info(f"       属性: {ext.attributes}")

    # 统计各类别数量
    from collections import Counter
    class_counts = Counter(ext.extraction_class for ext in result.extractions)
    logger.info(f"\n按类别统计:")
    for cls, count in class_counts.most_common():
        logger.info(f"   - {cls}: {count} 个")

except Exception as e:
    logger.error(f"❌ 提取失败: {type(e).__name__}: {str(e)}")
    import traceback
    logger.error(f"\n完整错误堆栈:")
    logger.error(traceback.format_exc())

logger.info("\n" + "="*60)
logger.info("测试完成")
logger.info("="*60)

