# GitHub 上传指南 / GitHub Upload Guide

[中文](#中文) | [English](#english)

---

<a name="中文"></a>

## 📦 准备上传到 GitHub

### 1. 初始化 Git 仓库（如果尚未初始化）

```bash
cd /Users/zhangxiaohang/Desktop/my_projects/llamaindex_langextract_rag
git init
```

### 2. 添加远程仓库

```bash
git remote add origin https://github.com/zkfws123/langextract_rag.git
```

### 3. 检查 .gitignore

确保以下文件/目录已被忽略：

```
# 已配置的忽略项
chroma_db/
outputs/api_config.json
outputs/*.html
.env
.env.local
__pycache__/
*.pyc
logs/
```

### 4. 添加所有文件

```bash
git add .
```

### 5. 提交更改

```bash
git commit -m "Initial commit: GraphRAG Knowledge Base System

- Intelligent knowledge extraction with LangExtract
- Hybrid retrieval (vector + graph)
- LangGraph agent for Q&A
- Streamlit UI with document preview and graph visualization
- Support for OpenAI, DeepSeek, Gemini, and custom APIs
- Standard open-source configuration (removed personal API gateways)"
```

### 6. 推送到 GitHub

```bash
# 首次推送（如果仓库为空）
git push -u origin main

# 或者，如果远程仓库已有内容
git pull origin main --rebase
git push origin main
```

### 7. 验证上传

访问 https://github.com/zkfws123/langextract_rag 确认文件已成功上传。

---

## 📋 上传前检查清单

- [x] README.md（中英文双语）
- [x] LICENSE（MIT 许可证）
- [x] .gitignore（已配置）
- [x] .env.example（环境变量模板）
- [x] requirements.txt（Python 依赖）
- [x] 移除个人 API 配置（Sonetto）
- [x] 标准化 LLM 配置（OpenAI, DeepSeek, Gemini, Custom）
- [x] 更新文档和代码注释

---

## 🔧 常见问题

### Q1: 如果远程仓库已有内容怎么办？

```bash
# 拉取远程内容并合并
git pull origin main --allow-unrelated-histories

# 解决冲突（如果有）
# 编辑冲突文件，然后：
git add .
git commit -m "Merge remote changes"
git push origin main
```

### Q2: 如何更新已上传的代码？

```bash
# 修改代码后
git add .
git commit -m "描述你的更改"
git push origin main
```

### Q3: 如何创建新分支？

```bash
# 创建并切换到新分支
git checkout -b feature/new-feature

# 推送新分支到远程
git push -u origin feature/new-feature
```

---

## 📝 推荐的 Commit 消息格式

```
<type>: <subject>

<body>

<footer>
```

**Type 类型：**
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构代码
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例：**

```bash
git commit -m "feat: add custom OpenAI-compatible API support

- Add custom API configuration in UI
- Support any OpenAI-compatible endpoint
- Update documentation"
```

---

## 🎯 GitHub 仓库设置建议

### 1. 添加 Topics（标签）

在 GitHub 仓库页面添加以下 topics：

```
graphrag
knowledge-graph
rag
retrieval-augmented-generation
langchain
chromadb
streamlit
llm
knowledge-extraction
question-answering
```

### 2. 设置 About（关于）

```
A powerful GraphRAG knowledge base system combining structured extraction, vector search, and knowledge graph for intelligent Q&A
```

### 3. 启用 Issues 和 Discussions

在仓库设置中启用：
- Issues（问题跟踪）
- Discussions（讨论区）

### 4. 添加 GitHub Actions（可选）

创建 `.github/workflows/test.yml` 用于自动化测试。

---

<a name="english"></a>

## 📦 Preparing for GitHub Upload

### 1. Initialize Git Repository (if not already initialized)

```bash
cd /Users/zhangxiaohang/Desktop/my_projects/llamaindex_langextract_rag
git init
```

### 2. Add Remote Repository

```bash
git remote add origin https://github.com/zkfws123/langextract_rag.git
```

### 3. Check .gitignore

Ensure the following files/directories are ignored:

```
# Configured ignore items
chroma_db/
outputs/api_config.json
outputs/*.html
.env
.env.local
__pycache__/
*.pyc
logs/
```

### 4. Add All Files

```bash
git add .
```

### 5. Commit Changes

```bash
git commit -m "Initial commit: GraphRAG Knowledge Base System

- Intelligent knowledge extraction with LangExtract
- Hybrid retrieval (vector + graph)
- LangGraph agent for Q&A
- Streamlit UI with document preview and graph visualization
- Support for OpenAI, DeepSeek, Gemini, and custom APIs
- Standard open-source configuration (removed personal API gateways)"
```

### 6. Push to GitHub

```bash
# First push (if repository is empty)
git push -u origin main

# Or, if remote repository has content
git pull origin main --rebase
git push origin main
```

### 7. Verify Upload

Visit https://github.com/zkfws123/langextract_rag to confirm files are uploaded successfully.

---

## 📋 Pre-Upload Checklist

- [x] README.md (bilingual: English & Chinese)
- [x] LICENSE (MIT License)
- [x] .gitignore (configured)
- [x] .env.example (environment variable template)
- [x] requirements.txt (Python dependencies)
- [x] Removed personal API configurations (Sonetto)
- [x] Standardized LLM configuration (OpenAI, DeepSeek, Gemini, Custom)
- [x] Updated documentation and code comments

---

## 🔧 Common Issues

### Q1: What if the remote repository already has content?

```bash
# Pull remote content and merge
git pull origin main --allow-unrelated-histories

# Resolve conflicts (if any)
# Edit conflicting files, then:
git add .
git commit -m "Merge remote changes"
git push origin main
```

### Q2: How to update uploaded code?

```bash
# After modifying code
git add .
git commit -m "Describe your changes"
git push origin main
```

### Q3: How to create a new branch?

```bash
# Create and switch to new branch
git checkout -b feature/new-feature

# Push new branch to remote
git push -u origin feature/new-feature
```

---

## 📝 Recommended Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation update
- `style`: Code formatting
- `refactor`: Code refactoring
- `test`: Testing related
- `chore`: Build/tools related

**Example:**

```bash
git commit -m "feat: add custom OpenAI-compatible API support

- Add custom API configuration in UI
- Support any OpenAI-compatible endpoint
- Update documentation"
```

---

## 🎯 GitHub Repository Settings Recommendations

### 1. Add Topics (Tags)

Add the following topics on the GitHub repository page:

```
graphrag
knowledge-graph
rag
retrieval-augmented-generation
langchain
chromadb
streamlit
llm
knowledge-extraction
question-answering
```

### 2. Set About (Description)

```
A powerful GraphRAG knowledge base system combining structured extraction, vector search, and knowledge graph for intelligent Q&A
```

### 3. Enable Issues and Discussions

Enable in repository settings:
- Issues (issue tracking)
- Discussions (discussion forum)

### 4. Add GitHub Actions (Optional)

Create `.github/workflows/test.yml` for automated testing.

---

## 📧 Contact

- GitHub: [@zkfws123](https://github.com/zkfws123)
- Repository: [https://github.com/zkfws123/langextract_rag](https://github.com/zkfws123/langextract_rag)

