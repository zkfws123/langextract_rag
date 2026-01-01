"""测试markdown fence剥离和monkey patch"""
import re

def _strip_markdown_fence(text: str) -> str:
    """Strip markdown code fence markers"""
    if not text:
        return text
    
    text = text.strip()
    pattern = r'^```(?:json|JSON)?\s*\n?(.*?)\n?```$'
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    return text

# Test cases
test_cases = [
    '```json\n{"test":"hello"}\n```',
    '```\n{"test":"hello"}\n```',
    '{"test":"hello"}',
    '```json\n{\n    "test": "hello"\n}\n```',
]

print("测试 _strip_markdown_fence:")
for test in test_cases:
    result = _strip_markdown_fence(test)
    print(f"\n输入: {repr(test)}")
    print(f"输出: {repr(result)}")


# Test monkey patch
print("\n\n测试 Monkey Patch:")

from langextract.core import format_handler
import json

original_parse = format_handler.FormatHandler.parse_output

def patched_parse(self, content: str, *args, **kwargs):
    print(f"[PATCH] 原始内容前50字符: {repr(content[:50])}")
    content = _strip_markdown_fence(content)
    print(f"[PATCH] 处理后内容前50字符: {repr(content[:50])}")
    return original_parse(self, content, *args, **kwargs)

format_handler.FormatHandler.parse_output = patched_parse

# Test with patched handler
handler = format_handler.FormatHandler()
test_json = '```json\n{"extractions": []}\n```'

try:
    result = handler.parse_output(test_json)
    print(f"\n✓ 解析成功: {result}")
except Exception as e:
    print(f"\n✗ 解析失败: {e}")
