"""通用文档知识提取配置"""
import textwrap
import langextract as lx

PROMPT = textwrap.dedent("""\
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

EXAMPLES = [
    lx.data.ExampleData(
        text="张三（清华大学）研究人工智能，参数量增长了300%。",
        extractions=[
            lx.data.Extraction(
                extraction_class="实体",
                extraction_text="张三",
                attributes={"类型": "人物", "机构": "清华大学"}
            ),
            lx.data.Extraction(
                extraction_class="实体",
                extraction_text="清华大学",
                attributes={"类型": "机构"}
            ),
            lx.data.Extraction(
                extraction_class="实体",
                extraction_text="人工智能",
                attributes={"类型": "技术术语"}
            ),
            lx.data.Extraction(
                extraction_class="数据指标",
                extraction_text="增长了300%",
                attributes={"指标": "参数量", "类型": "增长率"}
            ),
        ]
    )
]
