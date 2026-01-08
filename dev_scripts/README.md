# 开发测试脚本目录

本目录包含项目开发过程中使用的各种测试和调试脚本。

## 🧪 测试脚本分类

### 基础功能测试
- `quick_test.py` - 快速导入测试，验证项目依赖
- `test_api_connection.py` - API连接测试（LLM/Embedding）

### 提取功能测试
- `test_simple_extract.py` - 简单知识提取测试
- `test_extraction_fix.py` - 提取修复测试
- `test_extraction_a06fa667.py` - 特定提取场景测试
- `test_chunked_extraction.py` - 分块提取测试
- `test_langextract_payload_coercion.py` - LangExtract负载转换测试
- `test_ocr_doc_extraction.py` - OCR文档提取测试

### 功能模块测试
- `test_agent_logging.py` - Agent日志系统测试
- `test_kb_simple.py` - 知识库简单功能测试
- `test_patch.py` - 补丁功能测试
- `test_sonetto.py` - Sonetto网关测试

### 调试工具
- `debug_graph_search.py` - 图搜索调试
- `debug_langextract.py` - LangExtract调试
- `debug_ziwei_extraction_class.py` - 紫微斗数提取类调试

### 验证工具
- `find_validation.py` - 查找验证逻辑

## 📝 使用说明

### 快速验证项目环境
```bash
python dev_scripts/quick_test.py
```

### 测试API连接
```bash
python dev_scripts/test_api_connection.py
```

### 测试知识提取
```bash
python dev_scripts/test_simple_extract.py
```

### 测试Agent日志
```bash
python dev_scripts/test_agent_logging.py
```

### 调试图搜索
```bash
python dev_scripts/debug_graph_search.py
```

## 🔧 注意事项

1. 所有测试脚本应从项目根目录运行（通过 `python dev_scripts/xxx.py`）
2. 确保 `.env` 文件配置正确
3. 部分测试需要实际的API密钥和服务连接
4. 调试脚本可能包含临时代码，仅供开发使用

## 🚀 开发建议

- 新增测试脚本应放在此目录
- 测试脚本命名规范：`test_*.py`（单元测试）、`debug_*.py`（调试脚本）
- 保持脚本的独立性，避免相互依赖
- 重要的测试逻辑应迁移到 `tests/` 目录作为正式测试用例
