"""测试 extraction_text 类型修复"""
import sys
sys.path.insert(0, '.')

# 导入 knowledge_extractor 以应用 monkey patch
from src.parsers import knowledge_extractor

import langextract.core.data as lx_data
import json

print("测试 Extraction 对象创建...")
print("="*60)

# 测试1: 正常字符串
print("\n测试1: 正常字符串")
try:
    e1 = lx_data.Extraction('实体', '张三')
    print(f"✓ 成功: extraction_text={e1.extraction_text}, type={type(e1.extraction_text)}")
except Exception as ex:
    print(f"✗ 失败: {ex}")

# 测试2: dict 类型（有 'text' 键）
print("\n测试2: dict 类型（有 'text' 键）")
try:
    e2 = lx_data.Extraction('实体', {'text': '李四', 'other': 'data'})
    print(f"✓ 成功: extraction_text={e2.extraction_text}, type={type(e2.extraction_text)}")
except Exception as ex:
    print(f"✗ 失败: {ex}")

# 测试3: dict 类型（有 'value' 键）
print("\n测试3: dict 类型（有 'value' 键）")
try:
    e3 = lx_data.Extraction('实体', {'value': '王五', 'other': 'data'})
    print(f"✓ 成功: extraction_text={e3.extraction_text}, type={type(e3.extraction_text)}")
except Exception as ex:
    print(f"✗ 失败: {ex}")

# 测试4: dict 类型（无特殊键）
print("\n测试4: dict 类型（无特殊键）")
try:
    e4 = lx_data.Extraction('实体', {'foo': 'bar', 'baz': 'qux'})
    print(f"✓ 成功: extraction_text={e4.extraction_text}, type={type(e4.extraction_text)}")
    # 应该是 JSON 字符串
    parsed = json.loads(e4.extraction_text)
    print(f"  解析后: {parsed}")
except Exception as ex:
    print(f"✗ 失败: {ex}")

# 测试5: list 类型
print("\n测试5: list 类型")
try:
    e5 = lx_data.Extraction('实体', ['item1', 'item2'])
    print(f"✓ 成功: extraction_text={e5.extraction_text}, type={type(e5.extraction_text)}")
except Exception as ex:
    print(f"✗ 失败: {ex}")

# 测试6: int 类型
print("\n测试6: int 类型")
try:
    e6 = lx_data.Extraction('数据', 123)
    print(f"✓ 成功: extraction_text={e6.extraction_text}, type={type(e6.extraction_text)}")
except Exception as ex:
    print(f"✗ 失败: {ex}")

print("\n" + "="*60)
print("测试完成")

