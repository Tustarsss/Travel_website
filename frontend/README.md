# 个性化旅游系统 · 前端

该前端使用 **Vite + Vue 3 + TypeScript + Tailwind CSS** 构建，为后端的个性化旅游服务提供可视化界面，包括：

- **智能推荐**：基于兴趣、关键词与区域类型检索推荐区域列表。
- **路线规划**：输入图节点与策略后调用后端最优路径算法，展示节点序列与路段信息。
- **设施查询**：根据出发点、半径和类别筛选附近设施，返回最佳路线距离与耗时。

## 快速开始

```bash
npm install
npm run dev
```

应用默认调用 `http://localhost:8000/api/v1`。若后端地址不同，可在根目录创建 `.env` 或 `.env.local` 并设置：

```bash
VITE_API_BASE_URL=http://your-backend-host/api/v1
```

## 构建与检查

```bash
# 仅进行类型检查
npx vue-tsc --noEmit

# 构建生产产物
npm run build

# 预览构建结果
npm run preview
```

> 若在 Windows 上执行脚本遇到问题，可以依次运行 `npx vue-tsc --noEmit` 与 `npx vite build` 来完成相同的步骤。

## 主要目录结构

```
src/
 ├─ pages/             # 路由页面（推荐、路线、设施）
 ├─ router/            # Vue Router 配置
 ├─ services/          # Axios 实例与后端 API 封装
 ├─ types/             # 后端响应类型定义
 └─ style.css          # Tailwind 全局样式
```

## 后续工作

- 根据后端真实数据优化表单默认值与可选项。
- 在 Pinia 中引入持久化或跨页面共享状态（例如常用的 regionId、nodeId）。
- 扩充可视化组件（地图、高亮路径等）以提升交互体验。
