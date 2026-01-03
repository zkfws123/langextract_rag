# UI: 并行分块开关 + 运行日志面板 + iOS 风格美化

## 背景
当前提取与入库流程在前端主要依赖 `st.info/st.success` 的即时提示，缺少统一的“开始-结束”过程日志，排障时难以回看。
此外，分块并行的开关需要通过环境变量设置，不便于前端用户直接控制。

## 目标
- 前端提供并行分块提取开关与 workers 设置（侧边栏）。
- 前端新增日志面板，集中展示：解析/提取/关系抽取/入库/合并与失败堆栈等提示。
- 前端整体观感更贴近 iOS 风格：浅色背景、卡片化、圆角与柔和阴影。

## 范围
- Streamlit UI：`src/ui/app.py`、`src/ui/settings_sidebar.py`、`src/ui/doc_workflow.py`、`src/ui/session.py`。
- 后端参数透传：`src/parsers/pipeline.py`（新增 `parallel_workers` 参数透传到 `KnowledgeExtractor.extract_from_text`）。
- UI 日志基础设施：新增 `src/ui/ui_logger.py`（logging handler 写入 session_state）。

## 非目标
- 不做新的抽取/关系算法升级。
- 不引入新的前端框架（保持 Streamlit）。

## 验收标准
- 侧边栏可开关并行提取；开启后可设置 workers，提取时确实生效。
- 日志面板在“开始解析/解析完成/开始提取/提取完成/开始入库/入库完成”等节点输出日志，可清空。
- UI 样式整体更统一，侧边栏/Expander/输入控件圆角卡片化。
