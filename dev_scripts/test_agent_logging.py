"""
测试Agent日志功能
验证日志是否正确记录工具调用和对话过程
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

from src.retrieval.vector.chroma_store import ChromaVectorStore
from src.graph.in_memory_store import InMemoryGraphStore
from src.agents.agent import build_agent, agent_query

def test_agent_logging():
    """测试Agent日志功能"""

    print("=" * 80)
    print("开始测试Agent日志功能")
    print("=" * 80)

    # 知识库路径
    kb_path = Path("outputs/knowledge_bases/57e434ee")

    # 1. 加载知识图谱
    print("\n[1] 加载知识图谱...")
    graph_store = InMemoryGraphStore()
    graph_file = kb_path / "graph.json"
    if graph_file.exists():
        with open(graph_file, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        # InMemoryGraphStore 实际使用字段是 knowledge_graph={entities, relations}
        graph_store.knowledge_graph = {
            "entities": graph_data.get("entities", {}) or {},
            "relations": graph_data.get("relations", []) or [],
        }
        print(f"   ✅ 加载了 {len(graph_store.knowledge_graph['entities'])} 个实体")
        print(f"   ✅ 加载了 {len(graph_store.knowledge_graph['relations'])} 个关系")
    else:
        print(f"   ⚠️  图谱文件不存在: {graph_file}")

    # 2. 初始化向量库
    print("\n[2] 初始化向量库...")
    vector_store = ChromaVectorStore(
        collection_name="pdf_knowledge_graph",
        persist_dir="./chroma_db_chapter5"
    )
    print(f"   ✅ 向量库已初始化")

    # 2. 构建Agent
    print("\n[3] 构建Agent...")
    build_agent(vector_store, graph_store)
    print(f"   ✅ Agent已构建")

    # 3. 测试问题
    test_questions = [
        "四化是什么？",
        "命宫有什么作用？",
        "禄权科忌分别代表什么？"
    ]
    
    print("\n" + "=" * 80)
    print("开始测试对话（请查看控制台和日志文件）")
    print("日志文件位置: outputs/logs/agent_chat_YYYYMMDD.log")
    print("=" * 80)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n\n{'='*80}")
        print(f"测试问题 {i}/{len(test_questions)}")
        print(f"{'='*80}")
        
        result = agent_query(question)
        
        print(f"\n问题: {result['question']}")
        print(f"\n回答: {result['answer'][:200]}...")
        
        if result['evidence']:
            print(f"\n工具调用记录: {len(result['evidence'])} 条")
            for j, ev in enumerate(result['evidence'][:3], 1):
                print(f"  {j}. {ev['type']} - {ev.get('tool', 'N/A')}")
        else:
            print("\n⚠️  警告: 未调用任何工具！")
    
    print("\n\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
    print("\n请检查以下内容：")
    print("1. 控制台输出 - 应该看到INFO级别的日志")
    print("2. 日志文件 - outputs/logs/agent_chat_YYYYMMDD.log")
    print("   - 应该包含详细的DEBUG日志")
    print("   - 应该记录每次工具调用的参数和结果")
    print("   - 应该标记是否使用了知识库工具")
    print("\n如果Agent没有调用工具，日志会显示警告信息！")
    print("=" * 80)

if __name__ == "__main__":
    test_agent_logging()

