# 个性化旅游系统 · 前端

该前端使用 **Vite + Vue 3 + TypeScript + Tailwind CSS** 构建，为后端的个性化旅游服务提供可视化界面。核心页面与特性：

- **智能推荐**：基于兴趣、关键词与区域类型检索推荐区域列表，支持快捷兴趣标签与预设示例。
- **路线规划**：输入图节点与策略后调用后端最优路径算法，展示节点序列、路段信息与交通方式限制，并支持一键交换起终点。
- **设施查询**：根据出发点、半径和类别筛选附近设施，并高亮展示距离、耗时、节点序列等详情。
- **共享偏好设置**：使用 Pinia 在各页面保存最近一次的查询参数，表单会自动回填。
- **通用组件与组合式函数**：`PageSection`、`ErrorAlert`、`LoadingIndicator`、`EmptyState` 以及 `useApiRequest` 帮助统一 UI 与异步请求体验。

## 快速开始

1. 安装依赖并启动开发服务器：

	```bash
	npm install
	npm run dev
	```

2. 浏览器访问 `http://localhost:5173/` 即可看到前端页面。

应用默认调用 `http://localhost:8000/api/v1`。若后端地址不同，可在根目录创建 `.env` 或 `.env.local` 并设置：

```bash
VITE_API_BASE_URL=http://your-backend-host/api/v1
```

## 构建与检查

```bash
# 运行项目内置的类型检查脚本
npm run typecheck

# 如遇包管理器在 PowerShell 下退出码异常，可改用
#   npm run typecheck:app
#   npm run typecheck:node

# 构建生产产物
npm run build

# 预览构建结果
npm run preview
```
```bash
# 单独执行打包（开发阶段需要跳过类型检查时可使用）
npm run bundle

# 等价的原生命令
npx vue-tsc --noEmit -p tsconfig.app.json
npx vue-tsc --noEmit -p tsconfig.node.json
npx vite build
```

## 主要目录结构

```
src/
 ├─ pages/             # 路由页面（推荐、路线、设施）
 ├─ router/            # Vue Router 配置
 ├─ services/          # Axios 实例与后端 API 封装
 ├─ stores/            # Pinia 偏好状态（查询参数持久化）
 ├─ types/             # 后端响应类型定义
 ├─ components/ui/     # 通用 UI 组件（章节容器、加载态、空态等）
 ├─ composables/       # 通用组合式函数（如 useApiRequest）
 ├─ constants/         # 示例数据、标签映射等
 └─ style.css          # Tailwind 全局样式
```

## 后续工作

- 根据后端真实数据优化表单默认值与可选项。
- 在 Pinia 中引入持久化或跨页面共享状态（例如常用的 regionId、nodeId）。
- 扩充可视化组件（地图、高亮路径等）以提升交互体验。
