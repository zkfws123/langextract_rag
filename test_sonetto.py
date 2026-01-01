#!/usr/bin/env python3
"""测试 Sonetto LLM 提供商"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv(override=True)

# 读取 Sonetto 配置
SONETTO_API_KEY = os.getenv("SONETTO_API_KEY")
SONETTO_BASE_URL = os.getenv("SONETTO_BASE_URL")
MODEL_HIGH = os.getenv("SONETTO_MODEL_HIGH")
MODEL_GEMINI = os.getenv("SONETTO_MODEL_GEMINI")

print("=" * 60)
print("🔧 Sonetto LLM 配置测试")
print("=" * 60)
print(f"API Base URL: {SONETTO_BASE_URL}")
print(f"Model 1: {MODEL_HIGH}")
print(f"Model 2: {MODEL_GEMINI}")
print(f"API Key: {SONETTO_API_KEY[:20]}...")
print("=" * 60)

# 创建客户端
client = OpenAI(
    api_key=SONETTO_API_KEY,
    base_url=SONETTO_BASE_URL
)

# 测试函数
def test_model(model_name: str):
    """测试指定模型"""
    print(f"\n🧪 测试模型: {model_name}")
    print("-" * 60)
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": "你好，请用一句话介绍你自己"}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        answer = response.choices[0].message.content
        print(f"✅ 响应成功")
        print(f"📝 回答: {answer}")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败")
        print(f"错误信息: {str(e)}")
        return False

# 执行测试
print("\n" + "=" * 60)
print("开始测试...")
print("=" * 60)

success_count = 0

# 测试 gpt-5.2-high
if test_model(MODEL_HIGH):
    success_count += 1

# 测试 gemini-3-pro-preview-3
if test_model(MODEL_GEMINI):
    success_count += 1

# 测试结果
print("\n" + "=" * 60)
print("📊 测试结果")
print("=" * 60)
print(f"总测试数: 2")
print(f"成功: {success_count}")
print(f"失败: {2 - success_count}")

if success_count == 2:
    print("\n🎉 所有模型测试通过！")
else:
    print("\n⚠️  部分模型测试失败，请检查配置")
