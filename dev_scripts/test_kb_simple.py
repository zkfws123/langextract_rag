"""
简单测试：验证知识库加载和日志功能
"""
import json
from pathlib import Path
from src.graph.in_memory_store import InMemoryGraphStore
from src.retrieval.vector.chroma_store import ChromaVectorStore
from src.agents.agent import build_agent, agent_query

print("=" * 80)
print("测试知识库加载和Agent日志")
print("=" * 80)

# 1. 加载知识图谱
print("\n[1] 加载知识图谱...")
kb_path = Path("outputs/knowledge_bases/57e434ee")
graph_store = InMemoryGraphStore()

graph_file = kb_path / "graph.json"
if graph_file.exists():
    with open(graph_file, 'r', encoding='utf-8') as f:
        graph_data = json.load(f)
    # 正确的赋值方式：赋值给 knowledge_graph 而不是 entities/relations
    graph_store.knowledge_graph = graph_data

    entities_count = len(graph_data.get("entities", {}))
    relations_count = len(graph_data.get("relations", []))
    print(f"   ✅ 加载了 {entities_count} 个实体")
    print(f"   ✅ 加载了 {relations_count} 个关系")

    # 显示前3个实体
    print("\n   前3个实体示例:")
    for i, (name, data) in enumerate(list(graph_data.get("entities", {}).items())[:3], 1):
        print(f"   {i}. {name[:50]}... | 类型: {data.get('type')}")
else:
    print(f"   ❌ 图谱文件不存在")

# 2. 初始化向量库
print("\n[2] 初始化向量库...")
vector_store = ChromaVectorStore(
    collection_name="pdf_knowledge_graph",
    persist_dir="./chroma_db_chapter5"
)
print("   ✅ 向量库已初始化")

# 3. 构建Agent
print("\n[3] 构建Agent...")
build_agent(vector_store, graph_store)
print("   ✅ Agent已构建")

# 4. 测试单个问题
print("\n" + "=" * 80)
print("测试问题: 四化是什么？")
print("=" * 80)

result = agent_query("四化是什么？")

print(f"\n【回答】\n{result['answer']}\n")
print(f"【工具调用】共 {len(result['evidence'])} 条记录")

# 统计工具使用
tools_used = set()
for ev in result['evidence']:
    if ev['type'] == 'call':
        tools_used.add(ev['tool'])

if tools_used:
    print(f"使用的工具: {', '.join(tools_used)}")
else:
    print("⚠️  警告: 未使用任何工具！")

print("\n" + "=" * 80)
print("测试完成！请查看日志文件: outputs/logs/agent_chat_20260102.log")
print("=" * 80)

