"""
调试脚本：验证图谱数据加载和搜索
"""
import json
from pathlib import Path
from src.graph.in_memory_store import InMemoryGraphStore

print("=" * 80)
print("调试图谱加载和搜索")
print("=" * 80)

# 1. 加载图谱数据
kb_path = Path("outputs/knowledge_bases/57e434ee")
graph_file = kb_path / "graph.json"

with open(graph_file, 'r', encoding='utf-8') as f:
    graph_data = json.load(f)

print(f"\n[1] 图谱数据统计:")
print(f"   实体数量: {len(graph_data.get('entities', {}))}")
print(f"   关系数量: {len(graph_data.get('relations', []))}")

# 2. 显示前5个实体名称
print(f"\n[2] 前5个实体名称:")
for i, name in enumerate(list(graph_data.get('entities', {}).keys())[:5], 1):
    print(f"   {i}. {name}")

# 3. 创建图谱存储并加载数据
graph_store = InMemoryGraphStore()
graph_store.knowledge_graph = graph_data

print(f"\n[3] 图谱存储状态:")
print(f"   knowledge_graph['entities'] 数量: {len(graph_store.knowledge_graph.get('entities', {}))}")
print(f"   knowledge_graph['relations'] 数量: {len(graph_store.knowledge_graph.get('relations', []))}")

# 4. 测试搜索
test_queries = [
    "四化",
    "禄权科忌",
    "十二宫",
    "命宫"
]

print(f"\n[4] 测试图谱搜索:")
for query in test_queries:
    result = graph_store.search(query, hop=1)
    matched_count = len(result.get("matched_entities", []))
    print(f"   查询 '{query}' -> 匹配 {matched_count} 个实体")
    
    if matched_count > 0:
        print(f"      匹配的实体:")
        for name, data in result["matched_entities"][:2]:
            print(f"      - {name[:60]}...")

print("\n" + "=" * 80)
print("调试完成")
print("=" * 80)

