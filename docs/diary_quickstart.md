# 旅游日记功能快速启动指南

## 🚀 快速开始

### 前置条件
- Python 3.11+
- Node.js 18+
- uv (Python包管理器)
- npm

### 1. 启动后端

```bash
# 进入后端目录
cd backend

# 安装依赖（如果还没安装）
uv sync

# 启动开发服务器
uv run uvicorn app.main:app --reload
```

后端将在 http://localhost:8000 启动

- API文档：http://localhost:8000/docs
- 日记API基础路径：http://localhost:8000/api/v1/diaries

### 2. 启动前端

```bash
# 进入前端目录（新建终端窗口）
cd frontend

# 安装依赖（如果还没安装）
npm install

# 启动开发服务器
npm run dev
```

前端将在 http://localhost:5173 启动

- 日记页面：http://localhost:5173/diaries

---

## 🧪 测试API

### 使用Swagger UI（推荐）

1. 访问 http://localhost:8000/docs
2. 展开 `diaries` 标签
3. 尝试以下操作：

#### 创建测试日记
```json
POST /api/v1/diaries

{
  "title": "清华园秋日漫步",
  "summary": "金秋十月，清华园的银杏叶黄了",
  "content": "今天天气真好，漫步在清华园中，金黄的银杏叶随风飘落...",
  "region_id": 1,
  "tags": ["校园风光", "秋天", "银杏"],
  "media_urls": ["https://example.com/photo1.jpg"],
  "media_types": ["image"],
  "status": "published"
}
```

#### 获取推荐日记
```
GET /api/v1/diaries/recommendations?limit=10&sort_by=hybrid
```

#### 查看日记详情
```
GET /api/v1/diaries/1
```

#### 评分日记
```json
POST /api/v1/diaries/1/rate

{
  "score": 5,
  "comment": "写得真好！"
}
```

### 使用curl

```bash
# 创建日记
curl -X POST http://localhost:8000/api/v1/diaries \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试日记",
    "content": "这是一篇测试日记的内容...",
    "region_id": 1,
    "tags": ["测试"]
  }'

# 获取推荐
curl http://localhost:8000/api/v1/diaries/recommendations?limit=5

# 查看详情
curl http://localhost:8000/api/v1/diaries/1
```

---

## 🎨 使用前端界面

### 1. 访问日记页面

打开浏览器访问：http://localhost:5173/diaries

### 2. 功能说明

#### 筛选栏（左侧）
- **搜索框**：输入关键词搜索日记标题和内容
- **排序方式**：
  - 综合推荐：平衡热度、评分和兴趣
  - 热度优先：按浏览量排序
  - 评分优先：按评分排序
  - 最新发布：按时间排序
- **旅游目的地**：输入目的地名称筛选
- **兴趣标签**：点击标签筛选相关日记

#### 日记列表（右侧）
- 显示日记卡片网格
- 显示封面图、标题、摘要
- 显示热度、评分、评论数
- 显示作者和地点信息
- 显示标签

#### 操作按钮
- **撰写日记**：创建新日记（待实现编辑器）
- **日记卡片**：点击查看详情（待实现详情页）

---

## 📊 数据库准备

### 方式1：自动创建表（推荐开发环境）

后端启动时会自动创建表（如果配置了auto-create）。

### 方式2：手动创建表

```sql
-- 创建diaries表
CREATE TABLE diaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    region_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT NOT NULL,
    compressed_content BLOB,
    is_compressed BOOLEAN DEFAULT 0,
    media_urls TEXT DEFAULT '[]',
    media_types TEXT DEFAULT '[]',
    tags TEXT DEFAULT '[]',
    popularity INTEGER DEFAULT 0,
    rating REAL DEFAULT 0.0,
    ratings_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'published',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (region_id) REFERENCES regions(id)
);

-- 创建diary_ratings表
CREATE TABLE diary_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diary_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    score INTEGER NOT NULL CHECK (score >= 1 AND score <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (diary_id) REFERENCES diaries(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE (diary_id, user_id)
);

-- 创建diary_views表
CREATE TABLE diary_views (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diary_id INTEGER NOT NULL,
    user_id INTEGER,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (diary_id) REFERENCES diaries(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 创建diary_animations表
CREATE TABLE diary_animations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    diary_id INTEGER NOT NULL,
    generation_params TEXT DEFAULT '{}',
    video_url TEXT,
    thumbnail_url TEXT,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    task_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (diary_id) REFERENCES diaries(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX idx_diaries_user ON diaries(user_id);
CREATE INDEX idx_diaries_region ON diaries(region_id);
CREATE INDEX idx_diaries_title ON diaries(title);
CREATE INDEX idx_diaries_status ON diaries(status);
CREATE INDEX idx_diaries_popularity ON diaries(popularity DESC);
CREATE INDEX idx_diaries_rating ON diaries(rating DESC);
CREATE INDEX idx_diaries_created ON diaries(created_at DESC);

CREATE INDEX idx_diary_ratings_diary ON diary_ratings(diary_id);
CREATE INDEX idx_diary_ratings_user ON diary_ratings(user_id);

CREATE INDEX idx_diary_views_diary ON diary_views(diary_id);
CREATE INDEX idx_diary_views_user ON diary_views(user_id);

CREATE INDEX idx_diary_animations_diary ON diary_animations(diary_id);
```

### 插入测试数据

```sql
-- 插入测试日记（假设user_id=1和region_id=1存在）
INSERT INTO diaries (user_id, region_id, title, summary, content, tags, status)
VALUES 
(1, 1, '清华园的秋天', '金色的银杏叶飘落', '秋天的清华园特别美丽，银杏大道金黄一片...', '["校园风光", "秋天", "银杏"]', 'published'),
(1, 1, '西湖游记', '杭州西湖印象', '春天来到西湖，柳树依依，湖面如镜...', '["自然风光", "休闲"]', 'published'),
(1, 1, '故宫深度游', '探索紫禁城的历史', '今天终于有机会深度游览故宫，感受历史的厚重...', '["历史文化", "建筑"]', 'published');

-- 插入测试评分
INSERT INTO diary_ratings (diary_id, user_id, score, comment)
VALUES 
(1, 1, 5, '写得真好！'),
(2, 1, 4, '不错的游记');

-- 插入测试浏览记录
INSERT INTO diary_views (diary_id, user_id)
VALUES 
(1, 1),
(1, 1),
(2, 1);
```

---

## 🔧 常见问题

### Q1: 后端启动报错"模块未找到"

**解决方案**：
```bash
cd backend
uv sync  # 重新安装依赖
```

### Q2: 前端启动报错"找不到模块"

**解决方案**：
```bash
cd frontend
rm -rf node_modules
npm install  # 重新安装依赖
```

### Q3: API返回404

**检查**：
1. 后端是否正常运行（http://localhost:8000/docs）
2. 路由是否正确注册（检查`router.py`）
3. 数据库表是否存在

### Q4: 前端无法连接后端

**检查**：
1. CORS配置（`backend/app/core/app.py`）
2. API地址配置（`frontend/src/services/apiClient.ts`）
3. 后端是否在8000端口运行

### Q5: 数据库表不存在

**解决方案**：
- 方式1：手动执行上面的SQL语句
- 方式2：使用Alembic迁移（生产推荐）

---

## 📝 开发注意事项

### 1. 用户认证
当前所有API使用硬编码的`user_id=1`。在生产环境中需要：
- 实现JWT或Session认证
- 更新API端点获取真实用户ID

### 2. 数据库
当前使用SQLite，适合开发和小型应用。大规模应用建议：
- 迁移到PostgreSQL或MySQL
- 配置连接池
- 实现主从复制

### 3. 文件上传
当前只存储URL，需要实现：
- 图片/视频上传API
- CDN集成（七牛云/阿里云OSS）
- 图片压缩和缩略图生成

### 4. 性能优化
建议添加：
- Redis缓存（热门数据）
- 数据库查询优化
- 前端虚拟滚动

---

## 📚 相关文档

- [设计文档](./diary_feature_design.md) - 完整的技术设计
- [开发报告](./diary_development_report.md) - 进度总结
- [README](../README.md) - 项目总览

---

## 🆘 需要帮助？

如果遇到问题：
1. 查看API文档：http://localhost:8000/docs
2. 查看浏览器控制台（F12）
3. 查看后端日志输出
4. 参考设计文档中的技术说明

---

**最后更新**: 2025年10月3日  
**版本**: v1.0
