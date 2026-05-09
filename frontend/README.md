# 地质文献智能体 - 前端 (Geology Agent Frontend)

这是一个基于 React + TypeScript + Vite + Tailwind CSS + Shadcn UI 构建的现代前端应用，用于与地质文献智能体后端进行交互。

## 功能特性

- **智能问答 (Chat)**: 与智能体对话，支持 Markdown 渲染和流式响应。
- **文献检索 (Search)**: 基于 RAG (Retrieval-Augmented Generation) 的文献搜索，展示相关文献片段。
- **文献管理 (Documents)**: 查看、上传和管理知识库中的文献。
- **响应式设计**: 支持桌面和移动端布局。

## 快速开始

### 1. 安装依赖

确保你已安装 Node.js (推荐 v18+)。

```bash
cd frontend
npm install
```

### 2. 运行开发服务器

```bash
npm run dev
```

应用将在 `http://localhost:5173` 启动。

### 3. 构建生产版本

```bash
npm run build
```

## 配置

- **API 代理**: 在 `vite.config.ts` 中配置了 `/api` 代理到后端 `http://localhost:8000`。请确保后端服务在此端口运行。
- **Tailwind**: 样式配置在 `tailwind.config.js` 和 `src/index.css`。

## 目录结构

- `src/components`: UI 组件 (基于 Radix UI 和 Tailwind)
- `src/pages`: 页面组件 (Chat, Search, Documents)
- `src/services`: API 服务封装
- `src/lib`: 工具函数
