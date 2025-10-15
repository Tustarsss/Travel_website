# 旅行系统后端（Travel Backend）

基于 FastAPI 与 SQLModel 的旅行内容与地图服务后端，支持真实地图数据导入、日记内容管理与多种后台任务。

## 快速上手

1. **安装依赖**（推荐使用 [uv](https://github.com/astral-sh/uv)）：

	```powershell
	uv sync
	```

2. **启动开发服务器**：

	```powershell
	uv run uvicorn app.main:app --reload
	```

3. **运行测试**：

	```powershell
	uv run python -m pytest
	```

默认允许来自 Vite 开发服务器（`http://localhost:5173`、`http://127.0.0.1:5173`）的跨域请求。若需额外域名，可在项目根目录创建/修改 `.env`：

```bash
CORS_ALLOWED_ORIGINS="http://your-frontend-host,http://another-host"
```

多个地址以逗号分隔。

## 主要能力

- **真实地图整合**：与 OSM 数据对接，生成多地区的区域/建筑/设施/路网节点。地图数据可直接持久化到数据库。
- **图算法实现**：Dijkstra最短路径算法，支持距离和时间优化策略。
- **智能推荐**：基于兴趣标签和评分的景区推荐，TopK算法实现高效推荐。
- **设施查询**：基于实际步行距离的附近设施搜索，支持多种设施类别。
- **日记内容管理**：支持示例用户与日记的初始化，内容压缩、评分与多媒体字段均已建模。
- **异步任务与缓存**：提供基于 Redis 的缓存框架、后端异步任务骨架以及定时维护流程。
- **全文检索与推荐**：内置 FTS5 检索、评分体系与推荐算法，可在 `app` 模块中进一步扩展。
- **扩展脚本**：`scripts/` 目录包含索引初始化、特性演示等工具，便于本地或 CI 自动化。

## 项目结构

```
backend/
├── app/
│   ├── algorithms/      # 各种算法实现 (Dijkstra、搜索、压缩等)
│   ├── api/             # API路由定义
│   │   └── v1/
│   │       └── endpoints/  # 具体API端点
│   ├── core/            # 核心配置和依赖注入
│   ├── models/          # SQLModel数据模型
│   ├── repositories/    # 数据访问层
│   ├── schemas/         # Pydantic请求/响应模式
│   ├── services/        # 业务逻辑层
│   └── main.py          # FastAPI应用入口
├── data/                # 数据文件和样本
├── scripts/             # 维护和初始化脚本
├── tests/               # 测试文件
└── pyproject.toml       # 项目配置和依赖
```

## 数据流程

后端提供以真实地图数据为核心的数据管线：

1. **生成地图数据集**（调用 OSM 实际地点）：

	```powershell
	uv run python scripts/generate_data.py --seed 42 --regions 5
	```

	- 输出位于 `data/generated/`，包含 `regions.json`、`buildings.json`、`facilities.json`、`graph_nodes.json`、`graph_edges.json`。
	- 可使用 `--populate-db` 在生成后自动导入数据库；`--keep-existing` 可保留现有数据。

2. **初始化数据库**（导入地图并写入示例日记）：

	```powershell
	# 如果已生成数据，可直接使用 auto import
	uv run python scripts/init_db.py

	# 指定数据目录并保留现有数据
	uv run python scripts/init_db.py --dataset-dir data/generated --keep-existing
	```

	脚本会创建 SQLite 模式、导入真实地图 JSON，并从 `data/samples/` 目录下的 `sample_users.json`、`sample_diaries.json`、`sample_diary_ratings.json` 读取示例用户/日记/评分后写入数据库。

3. **维护辅助脚本**（按需执行）：

	```powershell
	uv run python scripts/init_fts.py          # 初始化全文索引
	uv run python scripts/optimize_indexes.py  # 优化数据库索引
	uv run python scripts/demo_features.py     # 展示后台能力
	```

## 核心API接口

### 景区推荐 (`/api/v1/recommendations`)
- `GET /regions` - 获取景区推荐列表

### 路线规划 (`/api/v1/routing`)
- `GET /routes` - 计算最优路径

### 设施查询 (`/api/v1/facilities`)
- `GET /nearby` - 查找附近设施

### 景区信息 (`/api/v1/regions`)
- `GET /{region_id}` - 获取景区详情
- `GET /{region_id}/nodes` - 获取景区节点
- `GET /{region_id}/edges` - 获取景区边

## 常见问题

- **地图数据不足**：`generate_data.py` 会在可配置地点列表中轮询，若未达到目标数量会抛出 `RealDataUnavailableError`，可在 `app/services/data_generation/generator.py` 中扩充地点。
- **跨域调试**：修改 `.env` 中的 `CORS_ALLOWED_ORIGINS` 后需重启应用。
- **路径规划无结果**：检查起终点是否在同一景区且存在可达路径。

更多架构说明与 API 细节请参阅 `app/` 目录内的模块文档与注释。

---

**最后更新**: 2025年10月15日
