"""最简单的LangExtract测试"""
import os
from dotenv import load_dotenv
load_dotenv(override=True)

import langextract as lx
from langextract.providers.openai import OpenAILanguageModel

# 配置
api_key = os.getenv("GEMINI_API_KEY")
base_url = os.getenv("GEMINI_BASE_URL")
model_id = "gemini-3-flash-preview"

print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
print(f"Base URL: {base_url}")
print(f"Model: {model_id}\n")

# 创建模型
model = OpenAILanguageModel(
    model_id=model_id,
    api_key=api_key,
    base_url=base_url,
)

# 最简单的测试
test_text = "破象是指生年四化象被同组或同类自化拉破。"
prompt = "提取专业术语"

print(f"测试文本: {test_text}")
print(f"Prompt: {prompt}\n")

try:
    print("开始提取...\n")
    result = lx.extract(
        text_or_documents=test_text,
        prompt_description=prompt,
        model=model,
        temperature=0,
        max_workers=1,
        show_progress=True,
    )
    
    print(f"\n✅ 成功！提取了 {len(result.extractions)} 个结果")
    
    for i, ext in enumerate(result.extractions, 1):
        print(f"\n结果 {i}:")
        print(f"  类别: {ext.extraction_class}")
        print(f"  文本: {ext.extraction_text}")
        print(f"  文本类型: {type(ext.extraction_text)}")
        
except Exception as e:
    print(f"\n❌ 失败: {type(e).__name__}")
    print(f"错误: {str(e)}")
    
    import traceback
    print("\n完整错误:")
    traceback.print_exc()

