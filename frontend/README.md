# 个性化旅游系统 · 前端

该前端使用 **Vite + Vue 3 + TypeScript + Tailwind CSS** 构建，为后端的个性化旅游服务提供可视化界面。核心页面与特性：

- **智能推荐**：基于兴趣、关键词与区域类型检索推荐区域列表，支持快捷兴趣标签与预设示例。
- **路线规划**：输入图节点与策略后调用后端最优路径算法，展示节点序列、路段信息与交通方式限制，并支持一键交换起终点。
- **路线地图**：规划结果生成后，在 Leaflet 地图中自动对齐节点与路径，提供起终点高亮和可视化图例。
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

## 路线地图可视化

- 当路线规划成功返回后，`Routing` 页面会自动渲染交互式地图：
	- 使用 `@vue-leaflet/vue-leaflet` + `leaflet` 的组合，默认加载 OpenStreetMap 瓦片。
	- 自动根据节点坐标调整视野并绘制路径折线，起点（绿色）与终点（红色）使用不同颜色突出显示。
	- 浮动图例标记起点 / 终点 / 路径，鼠标悬停节点可查看顺序与名称。
- Leaflet 样式已在 `src/main.ts` 中全局引入，额外样式位于 `RouteMap.vue` 内的 scoped 样式块。
- 后续可以在此基础上叠加地理围栏、交通方式图层或实时定位等扩展能力。

## 前后端联调与跨域

- 前端通过 `VITE_API_BASE_URL` 指向后端 API，如果使用 Docker 或云环境，请更新为对应的公网地址。
- FastAPI 后端默认允许来自 `http://localhost:5173` / `http://127.0.0.1:5173` 的跨域请求。若需要开放给其他来源，在后端根目录 `.env` 中加入：

	```bash
	CORS_ALLOWED_ORIGINS="http://your-frontend-host,http://another-host"
	```

	使用逗号分隔多条来源，修改后重启后端即可生效。

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
