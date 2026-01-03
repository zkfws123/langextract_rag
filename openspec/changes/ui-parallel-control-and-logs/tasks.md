# Tasks

- [ ] 在 `src/ui/session.py` 增加：并行设置与 UI 日志缓冲 state。
- [ ] 在 `src/ui/settings_sidebar.py` 增加并行开关 + workers。
- [ ] 在 `src/parsers/pipeline.py` 增加 `parallel_workers` 参数并透传。
- [ ] 在 `src/ui/doc_workflow.py` 将关键流程节点改成 `logger.info/exception`，方便写入日志面板。
- [ ] 新增 `src/ui/ui_logger.py`：logging handler 写入 session_state。
- [ ] 在 `src/ui/app.py`：初始化 UI logger + 增加底部“运行日志”expander。
- [ ] 在 `src/ui/app.py`：注入 iOS 风格 CSS（背景、卡片、圆角、sidebar 玻璃感等）。

## 验收
- 并行开关在 UI 可控，并对提取流程生效。
- 日志面板可看到完整“开始-结束”链路。
- 样式美化不影响现有功能。
