"""测试API连接脚本"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 测试配置
TEST_CONFIGS = [
    {
        "name": "主接口",
        "base_url": "https://vip.sonetto.top/v1",
    },
    {
        "name": "备用接口1",
        "base_url": "https://apis.sonetto.top/v1",
    },
    {
        "name": "备用接口2",
        "base_url": "https://api.sonetto.top/v1",
    },
]

def test_api(base_url: str, api_key: str, model: str = "gpt-4o-mini"):
    """测试API连接"""
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        
        print(f"  正在测试模型: {model}")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "你好，请回复'测试成功'"}
            ],
            max_tokens=10,
            temperature=0,
        )
        
        content = response.choices[0].message.content
        print(f"  ✅ 响应成功: {content}")
        return True
        
    except Exception as e:
        print(f"  ❌ 连接失败: {type(e).__name__}: {str(e)}")
        return False

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 错误: 未找到 OPENAI_API_KEY 环境变量")
        return
    
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    print("\n" + "="*60)
    
    # 测试所有配置
    for config in TEST_CONFIGS:
        print(f"\n【{config['name']}】")
        print(f"  URL: {config['base_url']}")
        
        # 测试 gpt-4o-mini
        success = test_api(config['base_url'], api_key, "gpt-4o-mini")
        
        if success:
            print(f"\n✅ {config['name']} 可用！")
            print(f"建议更新 .env 文件:")
            print(f"OPENAI_BASE_URL={config['base_url']}")
            break
    else:
        print("\n❌ 所有接口均不可用，请检查API配置")

if __name__ == "__main__":
    main()

