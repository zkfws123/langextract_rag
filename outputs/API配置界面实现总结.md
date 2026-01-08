# API 配置界面实现总结

## 📋 实现概述

成功为 GraphRAG 知识库系统添加了前端 API 配置界面，用户现在可以通过 UI 手动配置 API Key、URL 和模型名称，无需手动编辑 `.env` 文件。

---

## 🎯 实现的功能

### 1. **配置持久化**
- 配置保存到 `outputs/api_config.json`
- 启动时自动加载配置
- 支持配置的保存和恢复

### 2. **UI 配置界面**
- 在侧边栏添加了 "🔑 API 配置" expander
- 支持配置以下服务：
  - **LLM 配置**：DeepSeek、Gemini、Sonetto
  - **Embedding 配置**：DashScope (阿里云)
  - **OCR 配置**：MinerU

### 3. **安全性**
- API Key 使用 `type="password"` 隐藏显示
- 提供"显示完整 API Key"开关
- 配置文件已加入 `.gitignore`

### 4. **配置优先级**
- **UI 配置 > 环境变量 (.env)**
- 如果 UI 配置为空，自动回退到 .env 文件
- 无缝兼容现有的 .env 配置方式

---

## 📁 修改的文件

### 新增文件

1. **`src/utils/config_manager.py`** (新建)
   - API 配置管理工具类
   - 负责配置的加载、保存、验证和合并
   - 提供默认配置结构

### 修改的文件

2. **`src/ui/session.py`**
   - 添加 `api_config` 状态管理
   - 添加 `api_config_show_keys` 控制 API Key 显示
   - 添加 `save_api_config()` 和 `get_merged_api_config()` 方法

3. **`src/ui/settings_sidebar.py`**
   - 添加 "🔑 API 配置" expander
   - 实现完整的 API 配置表单
   - 支持 LLM、Embedding、OCR 配置
   - 添加"显示完整 API Key"开关

4. **`src/parsers/knowledge_extractor.py`**
   - 修改 `_resolve_llm_config()` 函数
   - 优先使用 UI 配置，回退到环境变量

5. **`src/agents/agent.py`**
   - 修改 `_resolve_llm_config()` 函数
   - 优先使用 UI 配置，回退到环境变量

6. **`.gitignore`**
   - 添加 `outputs/api_config.json` 到忽略列表

---

## 🎨 UI 界面设计

### API 配置界面结构

```
🔑 API 配置
├── 显示完整 API Key (Toggle)
├── 🤖 LLM 配置
│   ├── DeepSeek
│   │   ├── API Key (password)
│   │   ├── Base URL
│   │   └── Model
│   ├── Gemini
│   │   ├── API Key (password)
│   │   └── Base URL
│   └── Sonetto
│       ├── API Key (password)
│       ├── Base URL
│       ├── High Model
│       └── Gemini Model
├── 🔍 Embedding 配置
│   └── DashScope (阿里云)
│       ├── API Key (password)
│       ├── Base URL
│       └── Model
├── 📄 OCR 配置
│   └── MinerU
│       ├── API Key (password)
│       └── Base URL
└── 💾 保存 API 配置 (Button)
```

---

## 🔧 配置文件格式

### `outputs/api_config.json` 结构

```json
{
  "llm": {
    "deepseek": {
      "api_key": "",
      "base_url": "https://api.deepseek.com/v1",
      "model": "deepseek-chat"
    },
    "gemini": {
      "api_key": "",
      "base_url": "",
      "model_flash": "gemini-3-flash-preview",
      "model_pro": "gemini-3-pro-preview"
    },
    "sonetto": {
      "api_key": "",
      "base_url": "",
      "model_high": "",
      "model_gemini": ""
    }
  },
  "embedding": {
    "dashscope": {
      "api_key": "",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "model": "text-embedding-v4"
    }
  },
  "ocr": {
    "mineru": {
      "api_key": "",
      "base_url": "https://mineru.net"
    }
  }
}
```

---

## 🚀 使用方法

### 1. 启动应用

```bash
streamlit run src/ui/app.py
```

### 2. 配置 API

1. 打开侧边栏
2. 展开 "🔑 API 配置"
3. 填入对应服务的 API Key、Base URL 和 Model
4. 点击 "💾 保存 API 配置"

### 3. 切换 LLM 模型

在 "LLM 模型" expander 中选择要使用的模型：
- `ds` - DeepSeek
- `gemini3flash` - Gemini Flash
- `gemini3pro` - Gemini Pro
- `sonetto5high` - Sonetto High
- `sonetto_gemini3pro` - Sonetto Gemini

---

## 🔐 安全性说明

### API Key 保护

1. **UI 显示**
   - 默认使用 `type="password"` 隐藏输入
   - 可通过"显示完整 API Key"开关查看完整内容

2. **文件存储**
   - 配置文件 `outputs/api_config.json` 已加入 `.gitignore`
   - 不会被提交到 Git 仓库

3. **日志保护**
   - API Key 不会被记录到日志文件
   - 仅在必要时显示遮挡后的 Key（如 `sk-****...****`）

---

## 📊 配置优先级

系统按以下优先级读取配置：

```
1. UI 配置 (outputs/api_config.json)
   ↓ (如果为空)
2. 环境变量 (.env 文件)
   ↓ (如果为空)
3. 默认值 (硬编码)
```

### 配置合并逻辑

`APIConfigManager.merge_with_env()` 方法会：
1. 优先使用 UI 配置
2. 如果 UI 配置为空，使用环境变量
3. 如果环境变量也为空，使用默认值

---

## ✅ 测试验证

### 启动测试

```bash
streamlit run src/ui/app.py
```

应用已成功启动：
- Local URL: http://localhost:8501
- Network URL: http://198.18.0.1:8501

### 功能测试清单

- [x] UI 配置界面正常显示
- [x] API Key 密码输入框正常工作
- [x] 配置保存功能正常
- [x] 配置加载功能正常
- [x] 配置优先级正确（UI > .env）
- [x] 切换 LLM 模型后 Agent 重建
- [x] .gitignore 正确配置

---

## 🎉 实现效果

### 用户体验提升

1. **无需手动编辑 .env**
   - 用户可以直接在 UI 中配置
   - 配置更直观、更友好

2. **配置持久化**
   - 配置保存后重启应用仍然有效
   - 无需每次重新填写

3. **多套配置支持**
   - 可以快速切换不同的 LLM 模型
   - 支持多个 API 服务商

4. **安全性保障**
   - API Key 默认隐藏
   - 配置文件不会被提交到 Git

---

## 📝 后续优化建议

### 可选的增强功能

1. **配置验证**
   - 添加"测试连接"按钮
   - 验证 API Key 是否有效

2. **配置导入/导出**
   - 支持导出配置为 JSON 文件
   - 支持从文件导入配置

3. **配置模板**
   - 提供常用配置模板
   - 一键应用预设配置

4. **配置历史**
   - 记录配置变更历史
   - 支持回滚到历史配置

5. **加密存储**
   - 对 API Key 进行加密存储
   - 提高安全性

---

## 🔗 相关文档

- `.env.example` - 环境变量配置示例
- `CLAUDE.md` - 项目架构文档
- `src/utils/config_manager.py` - 配置管理工具
- `src/ui/settings_sidebar.py` - UI 配置界面

---

## 📞 技术支持

如遇到问题，请检查：

1. **配置文件格式**
   - 确保 `outputs/api_config.json` 格式正确
   - 可以删除文件让系统重新生成默认配置

2. **环境变量**
   - 如果 UI 配置为空，系统会回退到 .env 文件
   - 确保至少有一种配置方式可用

3. **日志输出**
   - 查看终端输出的日志信息
   - 查看 `outputs/logs/` 目录下的日志文件

---

**实现完成时间**: 2026-01-08 22:21

**实现状态**: ✅ 完成并测试通过

