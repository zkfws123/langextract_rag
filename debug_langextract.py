"""调试 langextract + gemini-3-pro 的 JSON 解析问题"""
import os
import sys
import textwrap
from dotenv import load_dotenv

# Import knowledge_extractor to apply the monkey patch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.parsers import knowledge_extractor

import langextract as lx
from langextract.providers.openai import OpenAILanguageModel
from openai import OpenAI

load_dotenv(override=True)

# 测试文本
test_text = """
紫微斗数是中国传统命理学的重要分支。生年四化代表着四种不同性质的影响：
禄——缘起，人缘佳；权——缘变，重血缘；科——缘显，展现才华；忌——缘灭，阻碍变化。
"""

# 提取配置
prompt = textwrap.dedent("""\
    从文档中提取以下结构化知识:
    - 实体: 人物、机构、地点、概念、技术术语
    - 术语定义: 专业术语及其解释
    """)

examples = [
    lx.data.ExampleData(
        text="张三（清华大学）研究人工智能",
        extractions=[
            lx.data.Extraction(
                extraction_class="实体",
                extraction_text="张三",
                attributes={"类型": "人物", "机构": "清华大学"}
            ),
        ]
    )
]

# 测试配置
test_configs = [
    {
        "name": "Sonetto - gpt-5.2-high",
        "api_key": os.getenv("SONETTO_API_KEY"),
        "base_url": os.getenv("SONETTO_BASE_URL"),
        "model": os.getenv("SONETTO_MODEL_HIGH"),
    },
    {
        "name": "Sonetto - gemini-3-pro-preview",
        "api_key": os.getenv("SONETTO_API_KEY"),
        "base_url": os.getenv("SONETTO_BASE_URL"),
        "model": os.getenv("SONETTO_MODEL_GEMINI"),
    },
    {
        "name": "DeepSeek",
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "base_url": os.getenv("DEEPSEEK_BASE_URL"),
        "model": os.getenv("DEFAULT_MODEL"),
    },
]


def test_raw_api_call(config):
    """测试原始API调用，看返回格式"""
    print(f"\n{'='*60}")
    print(f"原始API测试: {config['name']}")
    print(f"{'='*60}")
    
    try:
        client = OpenAI(
            api_key=config['api_key'],
            base_url=config['base_url']
        )
        
        # 简单的测试消息
        response = client.chat.completions.create(
            model=config['model'],
            messages=[
                {"role": "user", "content": "请用JSON格式返回: {'test': 'hello'}"}
            ],
            temperature=0,
        )
        
        content = response.choices[0].message.content
        print(f"✓ API调用成功")
        print(f"返回内容类型: {type(content)}")
        print(f"返回内容长度: {len(content) if content else 0}")
        print(f"返回内容前200字符:\n{content[:200] if content else 'EMPTY'}")
        
        return True
    except Exception as e:
        print(f"✗ API调用失败: {str(e)}")
        return False


def test_langextract_extraction(config, fence_output=True, force_json=False):
    """测试langextract提取"""
    print(f"\n{'='*60}")
    print(f"LangExtract测试: {config['name']}")
    print(f"fence_output={fence_output}, force_json={force_json}")
    print(f"{'='*60}")
    
    try:
        # 构建模型
        kwargs = None
        if force_json:
            kwargs = {"response_format": {"type": "json_object"}}
        
        model = OpenAILanguageModel(
            model_id=config['model'],
            api_key=config['api_key'],
            base_url=config['base_url'],
            kwargs=kwargs,
        )
        
        # 执行提取
        result = lx.extract(
            text_or_documents=test_text,
            prompt_description=prompt,
            examples=examples,
            model=model,
            fence_output=fence_output,
            use_schema_constraints=False,
            temperature=0,
            max_workers=1,
            show_progress=False,
        )
        
        print(f"✓ 提取成功")
        print(f"提取数量: {len(result.extractions) if result.extractions else 0}")
        if result.extractions:
            print(f"示例提取:")
            for ext in result.extractions[:3]:
                print(f"  - {ext.extraction_class}: {ext.extraction_text}")
        
        return True
    except Exception as e:
        print(f"✗ 提取失败: {type(e).__name__}: {str(e)}")
        import traceback
        print("\n完整错误:")
        traceback.print_exc()
        return False


def main():
    print("="*60)
    print("LangExtract + Gemini 调试测试")
    print("="*60)
    
    # 第一步：测试原始API调用
    print("\n\n第一步：测试原始API调用")
    print("-"*60)
    api_results = {}
    for config in test_configs:
        api_results[config['name']] = test_raw_api_call(config)
    
    # 第二步：测试不同的langextract配置
    print("\n\n第二步：测试LangExtract提取（不同配置）")
    print("-"*60)
    
    for config in test_configs:
        if not api_results.get(config['name']):
            print(f"\n跳过 {config['name']} (API测试失败)")
            continue
        
        # 测试三种配置组合
        configs_to_test = [
            {"fence_output": True, "force_json": False},
            {"fence_output": False, "force_json": True},
            {"fence_output": True, "force_json": True},
        ]
        
        for test_cfg in configs_to_test:
            success = test_langextract_extraction(
                config,
                fence_output=test_cfg["fence_output"],
                force_json=test_cfg["force_json"]
            )
            if success:
                print(f"  → 成功配置: fence_output={test_cfg['fence_output']}, force_json={test_cfg['force_json']}")
                break
    
    print("\n\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    main()
