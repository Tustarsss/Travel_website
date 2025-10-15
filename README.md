# 个性化旅游推荐系统

一个基于图算法的智能旅游推荐与路径规划系统，提供景区推荐、路线规划、场所查询和旅游日记功能。

## 项目概述

### 核心功能

1. **景区推荐** - 基于用户兴趣和偏好推荐旅游目的地
2. **路线规划** - 计算景区内两点间的最优路径
3. **场所查询** - 查找附近的服务设施（餐厅、洗手间等）
4. **旅游日记** - 记录和分享旅行体验

## 快速开始

### 环境要求

- **Node.js**: >= 18.0.0
- **Python**: >= 3.11
- **包管理器**: npm (前端), uv (后端)

### 前端开发
```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器 (http://localhost:5173)
npm run dev

# 构建生产版本
npm run build
```

### 后端开发
使用 uv 安装依赖
首先参考此网站安装uv:https://uv.doczh.com/getting-started/installation/#__tabbed_1_2
```bash
# 进入后端目录
cd backend
# 安装依赖
uv sync
# 首次使用需初始化数据库
uv run python scripts/init_db.py

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

### 2. 路线规划

**位置**: `/routing` (RoutingPage)

**功能描述**:
- 智能搜索选择景区和起终点
- 支持两种优化策略（距离最短/时间最短）
- 显示路径详情（总距离、预计时间、途经节点）
- 地图可视化路径

### 3. 场所查询

**位置**: `/facilities` (FacilitiesPage)

**功能描述**:
- 查找附近服务设施（餐厅、商店、洗手间等）
- 按**实际步行距离**（非直线距离）排序
- 支持类别过滤
- 显示详细路径和预计到达时间

### 4. 旅游日记

**位置**: `/diaries` (DiariesPage)

**功能描述**:
- 浏览和搜索旅游日记
- 按评分和热度排序
- 智能推荐相关日记
- 支持多媒体内容（图片、视频）
- 发布和管理个人日记
- 评分和评论功能

## 常见问题

### Q: 前端请求超时
A: 检查后端是否正常运行，默认 15 秒超时。

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

## 许可证

本项目采用 MIT 许可证。

## 联系方式

如有问题或建议，请通过以下方式联系:
- 提交 Issue
- 发送邮件至项目维护者

---

**最后更新**: 2025年10月15日