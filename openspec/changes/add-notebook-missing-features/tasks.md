# Task List: Add Notebook Missing Features

## Phase 1: 混合检索（优先级：HIGH）

### Task 1.1: 实现BM25全文检索
- [ ] 创建 `src/retrieval/fulltext/bm25_store.py`
- [ ] 从Notebook提取BM25索引代码
- [ ] 实现 `index_documents()` 和 `search()` 方法
- [ ] 保存/加载索引到run_cache

**预计代码量**: ~100 lines
**参考**: Notebook Cell #108 (735-759行)

### Task 1.2: 实现混合检索器
- [ ] 创建 `src/retrieval/hybrid/hybrid_retriever.py`
- [ ] 组合向量检索和BM25检索结果
- [ ] 实现加权融合算法（RRF或简单加权）
- [ ] 可配置权重参数

**预计代码量**: ~80 lines
**参考**: Notebook混合检索示例

### Task 1.3: UI集成混合检索配置
- [ ] 在侧边栏添加"检索策略"选项（纯向量/纯全文/混合）
- [ ] 混合模式下显示权重滑块
- [ ] 修改Agent工具使用HybridRetriever
- [ ] 在聊天界面显示检索来源标签

**预计代码量**: ~50 lines in app.py

---

## Phase 2: 成本统计（优先级：HIGH）

### Task 2.1: 实现Token追踪器
- [ ] 创建 `src/utils/cost_tracker.py`
- [ ] 装饰器拦截OpenAI API调用
- [ ] 累积input_tokens和output_tokens
- [ ] 计算DeepSeek价格（￥0.001/1K tokens）

**预计代码量**: ~60 lines

### Task 2.2: UI显示成本统计
- [ ] 侧边栏添加"💰 成本统计"面板
- [ ] 实时显示：总Token数、总费用
- [ ] 按阶段分组：解析、提取、问答
- [ ] 清空按钮重置统计

**预计代码量**: ~30 lines in app.py

---

## Phase 3: 图谱高级功能（优先级：MEDIUM）

### Task 3.1: 社区检测
- [ ] 创建 `src/graph/community.py`
- [ ] 实现Louvain算法（使用python-louvain）
- [ ] 为每个社区分配颜色
- [ ] 修改graph_vis.html着色逻辑

**预计代码量**: ~70 lines
**参考**: Notebook社区检测部分

### Task 3.2: 多跳推理
- [ ] 创建 `src/graph/multi_hop.py`
- [ ] 实现双向BFS路径查询
- [ ] Agent工具：find_path(entity1, entity2, max_hops)
- [ ] 返回路径上的所有实体和关系

**预计代码量**: ~90 lines

---

## Phase 4: 分层摘要（优先级：LOW）

### Task 4.1: 社区摘要生成
- [ ] 为每个社区生成局部摘要
- [ ] 保存到graph_data["communities"]
- [ ] LLM提示词：总结该社区的核心主题

**预计代码量**: ~50 lines

### Task 4.2: 全局Map-Reduce
- [ ] 实现Map阶段：对每个社区生成答案
- [ ] Reduce阶段：合并多个社区答案
- [ ] UI选项：开启/关闭分层摘要

**预计代码量**: ~80 lines

---

## 总结
- **Phase 1**: 180行代码，2-3小时
- **Phase 2**: 90行代码，1小时
- **Phase 3**: 160行代码，3小时
- **Phase 4**: 130行代码，2-3小时

**推荐顺序**: Task 1.1 → 1.2 → 2.1 → 2.2 → 1.3 → (后续可选)
