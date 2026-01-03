"""测试并行分块抽取功能"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到 path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(override=True)

import langextract as lx
from langextract.providers.openai import OpenAILanguageModel

def test_simple_extraction():
    """测试简单的实体抽取"""
    print("="*60)
    print("测试1: 简单文本抽取（无分块）")
    print("="*60)
    
    # 配置
    api_key = os.getenv("GEMINI_API_KEY")
    base_url = os.getenv("GEMINI_BASE_URL")
    model_id = "gemini-3-flash-preview"
    
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print(f"Base URL: {base_url}")
    print(f"Model: {model_id}")
    
    # 创建模型
    model = OpenAILanguageModel(
        model_id=model_id,
        api_key=api_key,
        base_url=base_url,
    )
    
    # 简单测试文本
    test_text = """
    # 破象论
    
    所谓破象，乃是指生年四化象被同组或同类自化拉破。
    
    破象的类型：
    1. 同类破象
    2. 同组破象
    """
    
    prompt = "从文本中提取专业术语和定义"
    
    try:
        print("\n开始提取...")
        result = lx.extract(
            text_or_documents=test_text,
            prompt_description=prompt,
            model=model,
            temperature=0,
            max_workers=1,  # 单线程测试
            show_progress=True,
        )
        
        print(f"\n✅ 提取成功！")
        print(f"提取结果数量: {len(result.extractions)}")
        
        for i, ext in enumerate(result.extractions, 1):
            print(f"\n提取 {i}:")
            print(f"  类别: {ext.extraction_class}")
            print(f"  文本: {ext.extraction_text}")
            print(f"  属性: {ext.attributes}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 提取失败: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_chunked_extraction():
    """测试分块并行抽取"""
    print("\n" + "="*60)
    print("测试2: 分块并行抽取")
    print("="*60)
    
    # 配置
    api_key = os.getenv("GEMINI_API_KEY")
    base_url = os.getenv("GEMINI_BASE_URL")
    model_id = "gemini-3-flash-preview"
    
    # 创建模型
    model = OpenAILanguageModel(
        model_id=model_id,
        api_key=api_key,
        base_url=base_url,
    )
    
    # 较长的测试文本（模拟需要分块的场景）
    test_text = """
    # 破象论
    
    所谓破象，乃是指生年四化象被同组或同类自化拉破。
    
    破象的类型：
    1. 同类破象：禄+自化禄
    2. 同组破象：生年禄+自化忌
    
    # 双象论
    
    双象构成的条件：生年象+生年象
    
    双象组合：
    1. 禄权双象=AB
    2. 禄科双象=AC
    
    # 三象一物论
    
    三象一物是指三个象共同构建出完整的人、事、物的象意组合。
    """ * 3  # 重复3次，增加文本长度
    
    prompt = "从文本中提取专业术语和定义"
    
    try:
        print(f"\n文本长度: {len(test_text)} 字符")
        print("开始分块并行提取...")
        
        result = lx.extract(
            text_or_documents=test_text,
            prompt_description=prompt,
            model=model,
            temperature=0,
            max_workers=3,           # 3个worker并行
            max_char_buffer=500,     # 分块大小：500字符
            extraction_passes=2,     # 2轮提取
            show_progress=True,
        )
        
        print(f"\n✅ 分块提取成功！")
        print(f"提取结果数量: {len(result.extractions)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 分块提取失败: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始测试并行分块抽取功能\n")
    
    # 测试1: 简单抽取
    success1 = test_simple_extraction()
    
    # 测试2: 分块并行抽取
    if success1:
        success2 = test_chunked_extraction()
    else:
        print("\n⚠️ 跳过测试2（测试1失败）")
        success2 = False
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"测试1（简单抽取）: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"测试2（分块并行）: {'✅ 通过' if success2 else '❌ 失败'}")

