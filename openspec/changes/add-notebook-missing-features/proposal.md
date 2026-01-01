# Add Notebook Missing Features

## Problem Statement
当前Streamlit应用与原始Notebook项目对比，缺失以下关键功能：
1. **混合检索**：全文检索（BM25/Elasticsearch）+ 向量检索（Chroma）的组合
2. **多跳推理**：基于图谱路径的推理查询
3. **社区检测**：图谱节点聚类分析
4. **分层摘要**：局部社区摘要 + 全局Map-Reduce合成
5. **成本统计**：LLM Token消耗实时追踪

## Scope
本次变更将从Notebook项目中移植上述功能到Streamlit应用，优先实现混合检索和成本统计，其他功能作为可选扩展。

## Success Criteria
- [ ] 混合检索可在UI中配置权重（向量:0.7, 全文:0.3）
- [ ] 全文检索集成到retrieval/fulltext模块
- [ ] Token消耗显示在侧边栏和聊天界面
- [ ] 图谱可视化支持社区着色
- [ ] 复用Notebook代码避免重复开发

## Architecture
```
src/
├── retrieval/
│   ├── hybrid/
│   │   ├── __init__.py
│   │   ├── hybrid_retriever.py  # 组合向量+全文检索
│   │   └── reranker.py           # 可选：重排序模块
│   └── fulltext/
│       ├── __init__.py
│       └── bm25_store.py         # BM25全文检索
├── graph/
│   ├── community.py              # 社区检测（Louvain/Label Propagation）
│   └── multi_hop.py              # 多跳推理查询
└── utils/
    └── cost_tracker.py           # Token消耗统计
```

## Implementation Plan
1. 从Notebook提取混合检索代码 → `src/retrieval/hybrid/`
2. 实现BM25Store（参考Notebook的全文检索部分）
3. 添加成本追踪器（装饰器模式，拦截LLM调用）
4. UI集成：侧边栏添加"检索配置"和"成本统计"面板
5. 可选：实现社区检测和多跳推理（Phase 2）

## Dependencies
- `rank-bm25`: BM25算法实现
- `python-louvain` or `networkx.algorithms.community`: 社区检测
- 无需新增向量库依赖

## Testing Strategy
- 单元测试：BM25Store的索引/检索正确性
- 集成测试：混合检索结果与纯向量检索对比
- 成本统计：验证Token计数准确性（对比API响应）
