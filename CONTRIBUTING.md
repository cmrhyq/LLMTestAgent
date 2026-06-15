# 贡献指南

我们非常欢迎并感谢您对本项目的贡献！

在您开始贡献之前，请花点时间阅读以下指导方针：

## 报告 Bug

* 在提交新的 Bug 报告之前，请**搜索**现有的 Issues，以确保该问题尚未被报告。
* 请提供清晰、简洁的标题。
* 在描述中，请提供重现该 Bug 的**完整步骤**、您的**操作系统**和**环境信息**。

## 提交新功能建议

* 在提交新功能建议之前，请**搜索**现有的 Issues。
* 请提供清晰、简洁的标题。
* 详细描述您希望添加的功能，以及它将如何解决现有的问题或带来价值。

## 开发环境配置

```bash
git clone https://github.com/cmrhyq/LLMTestAgent.git
cd LLMTestAgent

# 后端依赖
cd backend && uv sync --extra dev && cd ..

# 前端依赖
cd frontend && npm install && cd ..

# 安装 pre-commit hooks
cd backend && uv run pre-commit install && cd ..
```

## 提交代码更改 (Pull Request)

1. **Fork** 本仓库到您自己的 GitHub 账户。
2. 从 `main` 分支创建一个新的**分支**。
3. 在新分支上进行您的修改。
4. 确保代码通过 lint 检查（pre-commit hooks 会自动运行）。
5. 在提交时，请编写清晰、描述性的**提交信息**。
6. 提交 Pull Request (PR) 到本仓库的 `main` 分支。
7. 在 PR 描述中，清楚地说明您的更改内容和原因，并链接到相关的 Issue（例如：`Closes #123`）。

## 项目结构

```
LLMTestAgent/
├── backend/      # Python 后端（FastAPI + LangGraph）
├── frontend/     # React 前端（Vite + Tailwind + shadcn/ui）
├── doc/          # 项目文档
└── .github/      # CI 工作流
```

- 后端代码修改在 `backend/` 目录下进行
- 前端代码修改在 `frontend/` 目录下进行
- 根目录的 `.pre-commit-config.yaml` 统管前后端 lint

感谢您的贡献！
