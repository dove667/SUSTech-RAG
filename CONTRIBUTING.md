# Contributing

感谢你愿意改进这个项目。这个仓库现在同时包含后端 RAG 管线和前端 WebUI，改动很容易跨模块扩散；请把“可 review、可回滚、可验证”当作基本要求。

## 开始之前

建议先读：

1. [README.md](README.md)
2. [backend/README.md](backend/README.md)
3. [frontend/README.md](frontend/README.md)
4. [backend/docs/project-guide.md](backend/docs/project-guide.md)
5. [backend/docs/runbook.md](backend/docs/runbook.md)

## 本地开发

后端：

```bash
cd backend
uv sync --extra dev
uv run pytest
uv run ruff check .
```

前端：

```bash
cd frontend
npm install
npm run build
```

完整构建知识库：

```bash
cd backend
uv run sustech-rag crawl
uv run sustech-rag preprocess
uv run sustech-rag index
```

## 分支与提交

- 从最新 `main` 拉新分支，分支名尽量说明目的，例如 `feat/sse-cancel`、`fix/chroma-test-client`。
- 一个提交只做一类事情。不要把格式化、重命名、功能开发、删文件和修 bug 混在同一个提交里。
- commit message 写清楚“改了什么”和“为什么改”，不要只写 `update`、`fix`、`wip`。
- 提交前自己看一遍 `git diff --stat` 和 `git diff`。如果你自己都无法快速解释每个文件为什么变了，先整理再提交。
- 不要提交无关的自动生成文件、缓存、模型、数据、IDE 配置或临时调试输出。

## PR 规范

PR 应该小而清楚。请避免一次性提交上千行、几十个文件、跨前后端和文档的混合改动；这种 PR 很难 review，也很容易把 bug 藏进去。

每个 PR 至少说明：

- 背景：为什么需要这个改动。
- 范围：改了哪些模块，哪些没有改。
- 验证：跑过哪些命令，结果是什么。
- 风险：可能影响哪些路径，哪些地方需要 reviewer 重点看。

建议粒度：

- 小修复：几十行以内最好。
- 普通功能：尽量控制在一个模块或一个用户流程内。
- 大重构：先开 issue 或设计说明，拆成多个可独立验证的 PR。

如果 PR 里出现大量删除、新增、移动文件，请在描述里逐项解释原因。不要为了“看起来更整洁”随手搬目录、改命名或重排代码。

## 代码质量底线

- 先读现有实现，再动手。优先沿用当前模块边界和代码风格。
- 不要复制粘贴大段相似逻辑；如果确实需要抽象，抽象要小、命名要清楚。
- 不要把临时调试、硬编码本机路径、魔法常量、沉默的 `except Exception` 留在代码里。
- 不要用一大坨函数同时处理配置、I/O、业务逻辑、网络请求和 UI 状态。拆成可以单独测试的小块。
- 新增行为要有测试；修 bug 要尽量补回归测试。
- 修改 API、配置、目录、命令或默认行为时，必须同步更新 README/docs。
- 涉及跨平台行为时，使用 `pathlib` 和参数列表形式的 `subprocess`，避免拼 shell 字符串。

## Review 前自查

提交 PR 前请确认：

- `git status` 里没有意外文件。
- `git diff --check` 通过。
- 后端相关改动跑过 `uv run pytest`。
- 前端相关改动跑过 `npm run build`。
- 文档和代码没有互相矛盾。
- 删除文件、改配置、改默认端口、改数据格式都在 PR 描述里明确写了。

## 不要提交

- `.venv/`
- `.uv-cache/`
- `node_modules/`
- `dist/`
- `data/raw/`
- `data/interim/`
- `data/vector_store/`
- `data/cache/`
- `data/models/`
- `.env`
- 本地 IDE 配置和系统文件