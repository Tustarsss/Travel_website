# 个性化旅游推荐系统

一个基于图算法的智能旅游推荐与路径规划系统，提供景区推荐、路线规划、场所查询和旅游日记功能。

## 项目概述

### 核心功能

1. **景区推荐** - 基于用户兴趣和偏好推荐旅游目的地
2. **路线规划** - 计算景区内两点间的最优路径
3. **场所查询** - 查找附近的服务设施（餐厅、洗手间等）
4. **旅游日记** - 记录和分享旅行体验 ✨ **已完成**

### 技术栈

#### 前端
- **框架**: Vue 3 (Composition API) + TypeScript
- **构建工具**: Vite 7.1.7
- **UI**: Tailwind CSS 3.4.14
- **状态管理**: Pinia 3.0.3
- **路由**: Vue Router 4.5.1
- **地图**: Leaflet 1.9.4
- **HTTP客户端**: Axios 1.12.2

#### 后端
- **框架**: FastAPI
- **语言**: Python 3.11+
- **数据库**: SQLite (通过 SQLAlchemy)

## 项目结构

```
Travel_website/
├── frontend/                 # 前端项目
│   ├── src/
│   │   ├── assets/          # 静态资源
│   │   ├── components/      # Vue 组件
│   │   │   ├── map/        # 地图相关组件
│   │   │   └── ui/         # UI 基础组件
│   │   ├── composables/     # 组合式函数
│   │   ├── constants/       # 常量定义
│   │   ├── pages/           # 页面组件
│   │   ├── router/          # 路由配置
│   │   ├── services/        # API 服务
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── types/           # TypeScript 类型定义
│   │   ├── App.vue          # 根组件
│   │   └── main.ts          # 入口文件
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                  # 后端项目
│   ├── app/
│   │   ├── algorithms/      # 图算法实现
│   │   ├── api/             # API 路由
│   │   │   └── v1/
│   │   │       └── endpoints/  # API 端点
│   │   ├── models/          # 数据模型
│   │   ├── repositories/    # 数据访问层
│   │   ├── schemas/         # Pydantic 模式
│   │   ├── services/        # 业务逻辑层
│   │   └── main.py          # FastAPI 应用入口
│   ├── data/                # 数据文件
│   │   └── travel.db       # SQLite 数据库
│   └── pyproject.toml
│
└── docs/                     # 项目文档
```

## 快速开始

### 环境要求

- **Node.js**: >= 18.0.0
- **Python**: >= 3.11
- **包管理器**: npm (前端), uv (后端)

### 前端开发
```bash
#windows需要使用cmd
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器 (http://localhost:5173)
npm run dev

# 构建生产版本
npm run build

# 类型检查
npm run type-check

# 代码检查
npm run lint
```

### 后端开发

使用 uv 安装依赖
首先参考此网站安装uv:https://uv.doczh.com/getting-started/installation/#__tabbed_1_2
```bash
# 进入后端目录
cd backend
# 安装依赖
uv sync

# 启动开发服务器 (http://localhost:8000)
uv run uvicorn app.main:app --reload

# 或直接使用 uvicorn
uvicorn app.main:app --reload
```

### 访问应用

- **前端（正常使用）**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs (Swagger UI)
- **API 文档**: http://localhost:8000/redoc (ReDoc)

## 核心功能详解

### 1. 景区推荐

**位置**: `/` (HomePage)

**功能描述**:
- 根据关键词搜索景区
- 按用户兴趣标签过滤
- 支持多种排序方式（综合推荐/热门程度/评分）
- 按景区类型过滤（景区/校园）

**核心 API**:
```
GET /api/v1/recommendations/regions
参数:
  - limit: 返回数量
  - sort_by: 排序方式 (hybrid/popularity/rating)
  - interests: 兴趣标签数组
  - interests_only: 仅显示包含兴趣标签的景区
  - q: 搜索关键词
  - region_type: 景区类型 (scenic/campus)
```

**技术实现**:
- 后端使用 SQLAlchemy 查询数据库
- 支持模糊搜索和多条件过滤
- 前端使用 Pinia 保存用户偏好设置

### 2. 路线规划

**位置**: `/routing` (RoutingPage)

**功能描述**:
- 智能搜索选择景区和起终点
- 支持两种优化策略（距离最短/时间最短）
- 显示路径详情（总距离、预计时间、途经节点）
- 地图可视化路径

**核心 API**:
```
GET /api/v1/routing/routes
参数:
  - region_id: 区域ID
  - start_node_id: 起点节点ID
  - end_node_id: 终点节点ID
  - strategy: 优化策略 (distance/time)
  - transport_modes: 交通方式数组
```

**算法原理**:
- 使用 Dijkstra 最短路径算法
- 根据策略选择权重：
  - 距离优先：使用边的物理距离
  - 时间优先：`时间 = 距离 / (理想速度 × 拥挤度)`（存在问题，待解决）
- 支持交通方式过滤（步行/骑行/电瓶车）（存在问题，待解决）

**数据结构**:
```python
# 图节点
GraphNode: {
    id, name, latitude, longitude,
    region_id, building_id, facility_id
}

# 图边
GraphEdge: {
    start_node_id, end_node_id, distance,
    ideal_speed, congestion, transport_modes
}
```

### 3. 场所查询

**位置**: `/facilities` (FacilitiesPage)

**功能描述**:
- 查找附近服务设施（餐厅、商店、洗手间等）
- 按**实际步行距离**（非直线距离）排序
- 支持类别过滤和搜索
- 显示详细路径和预计到达时间

**核心 API**:
```
GET /api/v1/facilities/nearby
参数:
  - region_id: 区域ID
  - origin_node_id: 起点节点ID
  - radius_meters: 搜索半径（米）
  - limit: 返回数量（默认10）
  - strategy: 固定为 'distance'（步行距离）
  - category: 设施类别数组
```

**算法原理**:
- 使用 **Dijkstra 算法一次性计算所有可达节点**
- 支持的设施类别：
  - 餐厅 (restaurant)
  - 商店 (shop)
  - 洗手间 (restroom)
  - 停车场 (parking)
  - 医疗点 (medical)
  - 信息中心 (info_center)
  - 售票处 (ticket_office)
  - 观景台 (viewpoint)

**核心代码逻辑**:
```python
# 一次性计算从起点到所有可达节点的距离
reachable_paths = compute_reachable_nodes(
    origin_node_id,
    max_distance=radius_meters
)

# 过滤出有设施的节点
for node_id, path_info in reachable_paths.items():
    if node_id in facility_nodes:
        results.append({
            "distance": path_info["distance"],
            "time": path_info["time"],
            "path": path_info["path"]
        })
```

### 4. 旅游日记

**位置**: `/diaries` (DiariesPage)

**状态**: ✨ **已完成基础功能**

**已实现功能**:
- ✅ 浏览和查询所有旅游日记
- ✅ 按热度、评价和个人兴趣智能推荐（TopK算法）
- ✅ 按目的地、标签筛选日记
- ✅ 关键词搜索（标题和摘要）
- ✅ 评分系统（1-5星）
- ✅ 浏览量统计（热度计算）
- ✅ 日记内容无损压缩（zlib）
- ✅ 支持文字、图片、视频记录
- ✅ 草稿和发布状态管理
- ✅ AIGC动画生成接口（占位符）

**核心算法**:
- **TopK推荐算法**：使用堆排序（`heapq.nlargest`），时间复杂度O(n log k)
- **混合评分**：综合热度（40%）+ 评分（40%）+ 兴趣匹配（20%）
- **无损压缩**：zlib压缩算法，自动判断压缩收益
- **高效查找**：数据库B树索引，支持精确查询

**待完善功能**:
- ⏳ 全文检索（FTS5）
- ⏳ 富文本编辑器
- ⏳ 文件上传（CDN集成）
- ⏳ AIGC实际集成（wan2.5）

**相关文档**:
- [设计文档](./docs/diary_feature_design.md) - 完整技术设计
- [开发报告](./docs/diary_development_report.md) - 进度总结
- [快速启动](./docs/diary_quickstart.md) - 使用指南

## 数据库结构

### 核心表

#### regions (景区信息)
```sql
- id: 主键
- name: 景区名称
- type: 类型 (scenic/campus)
- popularity: 热度评分
- rating: 用户评分
- description: 描述
- city: 所在城市
- latitude, longitude: 坐标
```

#### graph_nodes (图节点)
```sql
- id: 主键
- region_id: 所属景区
- name: 节点名称
- latitude, longitude: 坐标
- building_id: 关联建筑
- facility_id: 关联设施
- is_virtual: 是否虚拟节点
```

#### graph_edges (图边)
```sql
- id: 主键
- region_id: 所属景区
- start_node_id, end_node_id: 起终点
- distance: 距离（米）
- ideal_speed: 理想速度（米/分钟）
- congestion: 拥挤度系数
- transport_modes: 支持的交通方式
```

#### facilities (设施信息)
```sql
- id: 主键
- region_id: 所属景区
- name: 设施名称
- category: 类别
- latitude, longitude: 坐标
- description: 描述
```

## API 架构

### 分层设计

```
Controller (API Endpoints)
    ↓
Service (业务逻辑)
    ↓
Repository (数据访问)
    ↓
Model (数据模型)
```

### API 版本控制

- **基础路径**: `/api/v1`
- **端点分组**:
  - `/recommendations` - 推荐相关
  - `/routing` - 路由规划
  - `/facilities` - 设施查询
  - `/regions` - 景区信息

### 错误处理

HTTP 状态码规范:
- `200` - 成功
- `400` - 请求参数错误
- `404` - 资源不存在
- `500` - 服务器内部错误

错误响应格式:
```json
{
  "detail": "错误详细信息"
}
```

## 前端架构

### 组件结构

#### UI 基础组件 (components/ui/)
- `PageSection.vue` - 页面区块容器
- `ErrorAlert.vue` - 错误提示
- `LoadingIndicator.vue` - 加载指示器
- `EmptyState.vue` - 空状态占位
- `KeywordSearchSelect.vue` - 关键词搜索选择器

#### 地图组件 (components/map/)
- `RouteMap.vue` - 路线地图展示

#### 页面组件 (pages/)
- `HomePage.vue` - 景区推荐
- `RoutingPage.vue` - 路线规划
- `FacilitiesPage.vue` - 场所查询
- `DiariesPage.vue` - 旅游日记

### 状态管理

使用 Pinia 管理全局状态:

```typescript
// stores/preferences.ts
export const usePreferencesStore = defineStore('preferences', {
  state: () => ({
    recommendations: { /* 推荐偏好 */ },
    routing: { /* 路由偏好 */ },
    facilities: { /* 场所偏好 */ }
  }),
  persist: true  // 持久化到 localStorage
})
```

### 组合式函数 (Composables)

#### useApiRequest
通用 API 请求管理:
```typescript
const { data, error, loading, execute } = useApiRequest(apiFunction)
```

特性:
- 自动管理加载状态
- 错误处理
- 请求取消
- TypeScript 类型安全

### 路由配置

```typescript
const routes = [
  { path: '/', component: HomePage },
  { path: '/routing', component: RoutingPage },
  { path: '/facilities', component: FacilitiesPage },
  { path: '/diaries', component: DiariesPage }
]
```

### API 客户端配置

```typescript
// services/apiClient.ts
export const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 30_000,  // 30秒超时
})
```

## 性能优化

### 后端优化

1. **图数据缓存**
   - 边数据按区域ID缓存
   - 节点数据按节点ID缓存
   - 避免重复数据库查询

2. **批量查询**
   - 使用 SQLAlchemy 的 `get_nodes()` 批量获取节点
   - 减少数据库往返次数

### 前端优化

1. **防抖搜索**
   - 关键词搜索延迟 220ms
   - 避免频繁 API 调用

2. **请求取消**
   - 使用 requestToken 机制
   - 新请求自动取消旧请求

3. **状态持久化**
   - 用户偏好保存到 localStorage
   - 页面刷新后恢复状态

## 开发指南

### 添加新的 API 端点

1. **定义路由** (`backend/app/api/v1/endpoints/`)
```python
@router.get("/example")
async def example_endpoint(
    param: int = Query(...),
    service: Service = Depends(deps.get_service)
):
    result = await service.do_something(param)
    return result
```

2. **实现服务** (`backend/app/services/`)
```python
class Service:
    async def do_something(self, param: int):
        # 业务逻辑
        return result
```

3. **定义模式** (`backend/app/schemas/`)
```python
class ResponseModel(BaseModel):
    field: str
```

4. **前端调用** (`frontend/src/services/api.ts`)
```typescript
export const fetchExample = async (param: number) => {
  const { data } = await apiClient.get('/example', {
    params: { param }
  })
  return data
}
```

### 添加新的页面

1. **创建页面组件** (`frontend/src/pages/`)
```vue
<script setup lang="ts">
// 组件逻辑
</script>

<template>
  <!-- 页面内容 -->
</template>
```

2. **添加路由** (`frontend/src/router/index.ts`)
```typescript
{
  path: '/new-page',
  component: () => import('../pages/NewPage.vue')
}
```

3. **更新导航** (`frontend/src/App.vue`)

### 代码规范

#### TypeScript
- 使用严格模式
- 明确定义类型，避免 `any`
- 优先使用接口 (interface) 定义对象类型

#### Vue
- 使用 Composition API
- 组件使用 `<script setup>` 语法
- Props 使用 TypeScript 类型定义

#### Python
- 遵循 PEP 8 规范
- 使用类型注解
- 异步函数使用 `async/await`

## 常见问题

### Q: 前端请求超时
A: 检查后端是否正常运行，默认 15 秒超时。

### Q: 后端数据库查询慢
A: 确保图数据已缓存，检查是否有大量重复查询。

### Q: 路径规划返回空结果
A: 检查起终点是否存在可达路径，交通方式是否匹配。

### Q: 场所查询没有结果
A: 检查搜索半径是否足够大，起点附近是否有设施。

### Q: 地图不显示
A: 检查 Leaflet 资源是否加载成功，浏览器控制台是否有错误。

## 测试

### 前端测试数据

- 景区名称: 清华大学/北京大学/西湖
- 常用地点: 教室/食堂/宿舍

### API 测试

使用 Swagger UI (http://localhost:8000/docs) 进行交互式测试。

## 部署

### 前端部署

```bash
npm run build
# 将 dist/ 目录部署到静态服务器
```

### 后端部署

```bash
# 使用 gunicorn 或 uvicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 贡献指南（更建议问ai/上网查）

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证。

## 联系方式

如有问题或建议，请通过以下方式联系:
- 提交 Issue
- 发送邮件至项目维护者

---

**最后更新**: 2025年10月2日
