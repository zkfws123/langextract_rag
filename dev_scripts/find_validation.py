"""查找 langextract 中验证 extraction_text 类型的代码"""
import os
import langextract

path = os.path.dirname(langextract.__file__)
print(f"LangExtract 安装路径: {path}")
print("="*60)

# 搜索包含 "must be a string, integer, or float" 的文件
search_text = "must be a string, integer, or float"
found_files = []

for root, dirs, filenames in os.walk(path):
    for filename in filenames:
        if filename.endswith('.py'):
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if search_text.lower() in content.lower():
                        found_files.append(filepath)
                        print(f"\n找到匹配: {filepath}")
                        # 打印相关行
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if search_text.lower() in line.lower():
                                # 打印前后3行
                                start = max(0, i-4)
                                end = min(len(lines), i+3)
                                print(f"\n  上下文 (行 {start+1}-{end}):")
                                for j in range(start, end):
                                    marker = ">>>" if j == i-1 else "   "
                                    print(f"  {marker} {j+1:4d}: {lines[j]}")
            except Exception as e:
                pass

if not found_files:
    print("\n未找到包含该错误消息的文件")
else:
    print(f"\n\n总共找到 {len(found_files)} 个文件")

