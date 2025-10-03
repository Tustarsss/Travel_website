# 旅游日记功能设计文档

## 1. 功能概述

旅游日记管理是个性化旅游推荐系统的核心功能之一，允许用户记录、分享和浏览旅游经历，并通过智能算法实现日记推荐、搜索和生成。

### 1.1 核心功能清单

#### 基础功能
- ✅ 日记CRUD（创建、读取、更新、删除）
- ✅ 支持富文本内容（文字、图片、视频）
- ✅ 日记草稿和发布状态管理
- ✅ 用户评分和评论系统
- ✅ 浏览量统计（热度计算）

#### 查询与推荐
- ✅ 按热度、评分、兴趣推荐（TopK算法）
- ✅ 按目的地查询并排序
- ✅ 按名称精确查询（高效索引）
- ✅ 全文检索（FTS5）

#### 高级功能
- ✅ 日记内容无损压缩（zlib）
- ✅ AIGC旅游动画生成（wan2.5集成）
- ✅ 标签系统（用户兴趣匹配）

---

## 2. 数据库设计

### 2.1 现有模型分析

项目已有以下模型：

```python
# app/models/diaries.py
class Diary(BaseModel):
    user_id: int              # 作者ID
    region_id: int            # 关联景区
    title: str                # 标题
    summary: Optional[str]    # 摘要
    content: str              # 内容（原始）
    compressed_content: Optional[bytes]  # 压缩内容
    media_urls: List[str]     # 媒体URL列表
    media_types: List[DiaryMediaType]  # 媒体类型
    tags: List[str]           # 标签
    popularity: int           # 热度（浏览量）
    rating: float             # 平均评分
    ratings_count: int        # 评分人数
    status: DiaryStatus       # 状态（draft/published）

class DiaryRating(BaseModel):
    diary_id: int             # 日记ID
    user_id: int              # 评分用户ID
    score: int                # 评分（1-5）
    comment: Optional[str]    # 评论
```

### 2.2 需要补充的模型

#### DiaryView（浏览记录）
```python
class DiaryView(TimestampMixin, BaseModel, table=True):
    """日记浏览记录，用于统计热度和防重复计数"""
    __tablename__ = "diary_views"
    
    diary_id: int = Field(foreign_key="diaries.id", index=True)
    user_id: Optional[int] = Field(foreign_key="users.id", index=True)  # 可选，支持匿名
    ip_address: Optional[str] = None  # 防刷机制
    user_agent: Optional[str] = None
    
    # 索引：diary_id, user_id 组合索引
```

#### DiaryAnimation（AIGC生成的动画）
```python
class DiaryAnimation(TimestampMixin, BaseModel, table=True):
    """AIGC生成的旅游动画"""
    __tablename__ = "diary_animations"
    
    diary_id: int = Field(foreign_key="diaries.id", index=True)
    generation_params: dict = Field(sa_column=Column(JSON))  # 生成参数
    video_url: str  # 生成的动画URL
    thumbnail_url: Optional[str] = None
    status: str  # pending/processing/completed/failed
    error_message: Optional[str] = None
```

### 2.3 数据库索引策略

```sql
-- 核心查询索引
CREATE INDEX idx_diaries_region_status ON diaries(region_id, status);
CREATE INDEX idx_diaries_popularity ON diaries(popularity DESC);
CREATE INDEX idx_diaries_rating ON diaries(rating DESC);
CREATE INDEX idx_diaries_created_at ON diaries(created_at DESC);

-- 复合索引（推荐算法优化）
CREATE INDEX idx_diaries_composite ON diaries(status, region_id, popularity DESC, rating DESC);

-- 全文检索索引（SQLite FTS5）
CREATE VIRTUAL TABLE diaries_fts USING fts5(
    diary_id UNINDEXED,
    title,
    summary,
    content,
    tags
);
```

---

## 3. 核心算法设计

### 3.1 TopK推荐算法

#### 需求分析
- 用户通常只看前10个日记
- 不需要完全排序所有日记
- 数据动态变化频繁
- 需要支持多种排序策略

#### 算法选择：快速选择（QuickSelect）+ 堆排序

```python
class DiaryRankingAlgorithm:
    """日记排序算法实现"""
    
    def top_k_by_score(
        self,
        candidates: List[Diary],
        k: int,
        score_func: Callable[[Diary], float]
    ) -> List[Diary]:
        """
        使用快速选择算法找出TopK日记
        时间复杂度：O(n) 平均，O(n²) 最坏
        空间复杂度：O(k)
        """
        if len(candidates) <= k:
            return sorted(candidates, key=score_func, reverse=True)
        
        # 使用堆维护TopK
        import heapq
        return heapq.nlargest(k, candidates, key=score_func)
    
    def hybrid_score(self, diary: Diary, interests: List[str]) -> float:
        """
        综合评分函数
        score = 0.4 * normalized_popularity + 0.4 * rating + 0.2 * interest_match
        """
        # 热度归一化（log处理避免热门日记过度占优）
        popularity_score = math.log(diary.popularity + 1) / math.log(1000)
        popularity_score = min(popularity_score, 1.0)
        
        # 评分归一化
        rating_score = diary.rating / 5.0
        
        # 兴趣匹配（标签交集）
        if interests:
            match_count = len(set(diary.tags) & set(interests))
            interest_score = min(match_count / len(interests), 1.0)
        else:
            interest_score = 0.0
        
        return (
            0.4 * popularity_score +
            0.4 * rating_score +
            0.2 * interest_score
        )
```

#### 排序策略
1. **热度排序**：`ORDER BY popularity DESC`
2. **评分排序**：`ORDER BY rating DESC, ratings_count DESC`
3. **综合推荐**：使用 `hybrid_score` 函数
4. **最新发布**：`ORDER BY created_at DESC`

### 3.2 高效查找算法

#### 按名称精确查询
使用数据库B树索引：
```sql
-- 创建唯一索引
CREATE UNIQUE INDEX idx_diaries_title ON diaries(title) WHERE status = 'published';

-- 查询
SELECT * FROM diaries WHERE title = ? AND status = 'published';
```

#### 按目的地查询
利用复合索引：
```sql
-- 已有索引
CREATE INDEX idx_diaries_region_status ON diaries(region_id, status);

-- 查询
SELECT * FROM diaries 
WHERE region_id = ? AND status = 'published'
ORDER BY popularity DESC;
```

### 3.3 全文检索算法

#### SQLite FTS5实现

```python
class DiarySearchService:
    """全文检索服务"""
    
    async def full_text_search(
        self,
        query: str,
        limit: int = 20
    ) -> List[Diary]:
        """
        使用FTS5进行全文检索
        支持：中文分词、相关度排名、高亮显示
        """
        # FTS5查询语法
        sql = """
        SELECT d.*, 
               bm25(diaries_fts) as relevance_score
        FROM diaries_fts fts
        JOIN diaries d ON d.id = fts.diary_id
        WHERE diaries_fts MATCH ?
        ORDER BY relevance_score
        LIMIT ?
        """
        
        # 查询处理
        processed_query = self._process_query(query)
        results = await self.db.execute(sql, (processed_query, limit))
        return results
    
    def _process_query(self, query: str) -> str:
        """
        处理查询字符串
        - 支持分词
        - 支持布尔运算符（AND, OR, NOT）
        - 支持短语搜索
        """
        # 简单分词（生产环境建议使用jieba）
        tokens = query.split()
        # 使用OR连接多个词（提高召回率）
        return ' OR '.join(f'"{token}"' for token in tokens)
```

#### 搜索优化策略
1. **索引更新**：异步批量更新，避免影响主流程
2. **缓存热门搜索**：Redis缓存高频查询结果
3. **搜索历史**：记录用户搜索，用于推荐

### 3.4 无损压缩算法

#### zlib压缩实现

```python
import zlib

class DiaryCompressionService:
    """日记内容压缩服务"""
    
    COMPRESSION_LEVEL = 6  # 平衡压缩率和速度
    MIN_COMPRESS_SIZE = 1024  # 小于1KB不压缩
    
    def compress_content(self, content: str) -> bytes:
        """压缩日记内容"""
        content_bytes = content.encode('utf-8')
        
        if len(content_bytes) < self.MIN_COMPRESS_SIZE:
            return content_bytes  # 太小不压缩
        
        compressed = zlib.compress(content_bytes, self.COMPRESSION_LEVEL)
        
        # 计算压缩率
        ratio = len(compressed) / len(content_bytes)
        if ratio > 0.9:  # 压缩率不足10%，不压缩
            return content_bytes
        
        return compressed
    
    def decompress_content(self, compressed: bytes) -> str:
        """解压日记内容"""
        try:
            decompressed = zlib.decompress(compressed)
            return decompressed.decode('utf-8')
        except zlib.error:
            # 可能未压缩，直接解码
            return compressed.decode('utf-8')
```

#### 存储策略
- 创建时自动压缩：`compressed_content = compress(content)`
- 读取时自动解压：返回 `content` 字段时优先使用压缩版本
- 定期压缩：后台任务压缩历史日记

---

## 4. API设计

### 4.1 端点规划

基础路径：`/api/v1/diaries`

#### 日记CRUD
```
POST   /diaries                    创建日记
GET    /diaries/{id}               获取日记详情
PUT    /diaries/{id}               更新日记
DELETE /diaries/{id}               删除日记
GET    /diaries                    列出日记（带分页和筛选）
```

#### 推荐与搜索
```
GET    /diaries/recommendations    推荐日记（TopK）
GET    /diaries/search             全文检索
POST   /diaries/{id}/view          记录浏览
POST   /diaries/{id}/rate          评分
```

#### AIGC功能
```
POST   /diaries/{id}/generate-animation    生成动画
GET    /diaries/{id}/animations            获取动画列表
```

### 4.2 请求/响应示例

#### GET /diaries/recommendations

**请求参数**：
```typescript
{
  limit?: number              // 默认10，最大50
  sort_by?: 'hybrid' | 'popularity' | 'rating' | 'latest'
  interests?: string[]        // 用户兴趣标签
  region_id?: number         // 按目的地筛选
  q?: string                 // 关键词搜索
}
```

**响应**：
```json
{
  "items": [
    {
      "id": 1,
      "title": "西湖秋游记",
      "summary": "深秋的西湖别有一番韵味...",
      "author": {
        "id": 1,
        "username": "traveler",
        "display_name": "旅行者"
      },
      "region": {
        "id": 1,
        "name": "西湖",
        "type": "scenic"
      },
      "cover_image": "https://example.com/image.jpg",
      "tags": ["自然风光", "休闲"],
      "popularity": 1250,
      "rating": 4.8,
      "ratings_count": 42,
      "created_at": "2025-09-15T10:30:00Z",
      "score": 0.92  // 推荐分数
    }
  ],
  "total": 156,
  "page": 1,
  "page_size": 10,
  "sort_by": "hybrid"
}
```

#### POST /diaries

**请求体**：
```json
{
  "title": "清华园春日漫步",
  "summary": "樱花盛开的季节...",
  "content": "详细的日记内容（支持Markdown）...",
  "region_id": 5,
  "tags": ["校园风光", "春天", "樱花"],
  "media_urls": [
    "https://example.com/photo1.jpg",
    "https://example.com/photo2.jpg"
  ],
  "media_types": ["image", "image"],
  "status": "published"
}
```

**响应**：
```json
{
  "id": 42,
  "title": "清华园春日漫步",
  "created_at": "2025-10-03T14:20:00Z",
  "compressed": true,  // 内容已压缩
  "compression_ratio": 0.35  // 压缩率65%
}
```

#### GET /diaries/search

**请求参数**：
```typescript
{
  q: string                  // 搜索关键词（必填）
  limit?: number             // 默认20
  region_id?: number         // 按目的地筛选
}
```

**响应**：
```json
{
  "items": [
    {
      "id": 1,
      "title": "西湖秋游记",
      "summary": "深秋的<mark>西湖</mark>别有一番韵味...",  // 高亮匹配
      "relevance_score": 0.95,
      "matched_fields": ["title", "content"]
    }
  ],
  "query": "西湖",
  "total": 23,
  "execution_time_ms": 15
}
```

---

## 5. 前端界面设计

### 5.1 页面结构

```
DiariesPage.vue (主页面)
├── DiaryFilters.vue (筛选栏)
│   ├── 搜索框
│   ├── 排序选择器
│   ├── 目的地选择器
│   └── 兴趣标签选择器
├── DiaryList.vue (日记列表)
│   └── DiaryCard.vue (日记卡片) × N
├── DiaryDetail.vue (日记详情对话框)
│   ├── DiaryContent.vue (内容展示)
│   ├── MediaGallery.vue (媒体画廊)
│   ├── DiaryRating.vue (评分组件)
│   └── DiaryComments.vue (评论列表)
└── DiaryEditor.vue (日记编辑器)
    ├── RichTextEditor.vue (富文本编辑器)
    ├── MediaUploader.vue (媒体上传)
    ├── TagSelector.vue (标签选择)
    └── AnimationGenerator.vue (AIGC动画生成)
```

### 5.2 核心组件设计

#### DiaryCard.vue（日记卡片）
```vue
<template>
  <div class="diary-card">
    <!-- 封面图 -->
    <img :src="diary.cover_image" class="cover" />
    
    <!-- 标题和摘要 -->
    <div class="content">
      <h3 class="title">{{ diary.title }}</h3>
      <p class="summary">{{ diary.summary }}</p>
      
      <!-- 元信息 -->
      <div class="meta">
        <div class="author">
          <Avatar :user="diary.author" />
          <span>{{ diary.author.display_name }}</span>
        </div>
        <div class="stats">
          <span>👁️ {{ diary.popularity }}</span>
          <span>⭐ {{ diary.rating }}</span>
          <span>💬 {{ diary.comments_count }}</span>
        </div>
      </div>
      
      <!-- 标签 -->
      <div class="tags">
        <span v-for="tag in diary.tags" :key="tag" class="tag">
          {{ tag }}
        </span>
      </div>
    </div>
  </div>
</template>
```

#### DiaryEditor.vue（日记编辑器）
```vue
<template>
  <div class="diary-editor">
    <!-- 基本信息 -->
    <input v-model="form.title" placeholder="标题" />
    <textarea v-model="form.summary" placeholder="摘要" />
    
    <!-- 富文本编辑器 -->
    <RichTextEditor v-model="form.content" />
    
    <!-- 媒体上传 -->
    <MediaUploader 
      v-model:media-urls="form.media_urls"
      v-model:media-types="form.media_types"
      :max-files="10"
    />
    
    <!-- 目的地选择 -->
    <KeywordSearchSelect
      v-model="form.region_id"
      :search-fn="searchRegions"
      placeholder="选择旅游目的地"
    />
    
    <!-- 标签选择 -->
    <TagSelector v-model="form.tags" />
    
    <!-- 发布选项 -->
    <div class="actions">
      <button @click="saveDraft">保存草稿</button>
      <button @click="publish">发布</button>
    </div>
  </div>
</template>
```

### 5.3 状态管理（Pinia）

```typescript
// stores/diaries.ts
export const useDiariesStore = defineStore('diaries', {
  state: () => ({
    filters: {
      sortBy: 'hybrid' as DiarySort,
      interests: [] as string[],
      regionId: null as number | null,
      search: '',
    },
    currentDiary: null as Diary | null,
    userDiaries: [] as Diary[],
  }),
  
  actions: {
    async fetchRecommendations() {
      const data = await fetchDiaryRecommendations(this.filters)
      return data.items
    },
    
    async createDiary(diary: DiaryCreateRequest) {
      const newDiary = await createDiary(diary)
      this.userDiaries.unshift(newDiary)
      return newDiary
    },
    
    async viewDiary(diaryId: number) {
      // 记录浏览
      await recordDiaryView(diaryId)
      // 获取详情
      this.currentDiary = await fetchDiaryDetail(diaryId)
    },
  },
  
  persist: true,
})
```

---

## 6. AIGC动画生成集成

### 6.1 wan2.5 API调研

**注意**：wan2.5可能指的是"Wan秀"或其他视频生成AI。需要确认具体API。

假设API格式：
```typescript
interface AnimationGenerationRequest {
  images: string[]          // 图片URL列表
  description: string       // 文字描述
  style?: 'travel' | 'vlog' | 'cinematic'
  duration?: number         // 时长（秒）
}

interface AnimationGenerationResponse {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  video_url?: string
  progress?: number
}
```

### 6.2 实现流程

```python
class AIGCService:
    """AIGC动画生成服务"""
    
    async def generate_animation(
        self,
        diary: Diary,
        params: AnimationGenerationParams
    ) -> DiaryAnimation:
        """
        生成旅游动画
        1. 提取日记中的图片
        2. 调用wan2.5 API
        3. 异步等待生成完成
        4. 保存结果
        """
        # 1. 准备素材
        images = self._extract_images(diary)
        description = self._generate_description(diary)
        
        # 2. 调用API
        task_id = await self.wan25_client.create_task({
            'images': images,
            'description': description,
            'style': params.style,
        })
        
        # 3. 创建记录
        animation = DiaryAnimation(
            diary_id=diary.id,
            generation_params=params.dict(),
            status='pending',
        )
        await self.repo.save(animation)
        
        # 4. 异步任务等待完成
        asyncio.create_task(
            self._poll_generation_status(animation.id, task_id)
        )
        
        return animation
    
    async def _poll_generation_status(
        self,
        animation_id: int,
        task_id: str
    ):
        """轮询生成状态"""
        while True:
            status = await self.wan25_client.get_task_status(task_id)
            
            if status.status == 'completed':
                await self.repo.update(animation_id, {
                    'status': 'completed',
                    'video_url': status.video_url,
                })
                break
            elif status.status == 'failed':
                await self.repo.update(animation_id, {
                    'status': 'failed',
                    'error_message': status.error,
                })
                break
            
            await asyncio.sleep(5)  # 每5秒检查一次
```

### 6.3 前端集成

```vue
<template>
  <div class="animation-generator">
    <button @click="generate" :disabled="generating">
      {{ generating ? '生成中...' : '生成旅游动画' }}
    </button>
    
    <div v-if="animation" class="animation-result">
      <div v-if="animation.status === 'processing'" class="progress">
        <div class="progress-bar" :style="{width: progress + '%'}"></div>
        <span>生成进度：{{ progress }}%</span>
      </div>
      
      <video v-if="animation.status === 'completed'" 
             :src="animation.video_url" 
             controls>
      </video>
      
      <div v-if="animation.status === 'failed'" class="error">
        生成失败：{{ animation.error_message }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const generating = ref(false)
const animation = ref<DiaryAnimation | null>(null)
const progress = ref(0)

const generate = async () => {
  generating.value = true
  try {
    animation.value = await generateDiaryAnimation(props.diaryId)
    
    // 轮询状态
    const interval = setInterval(async () => {
      const updated = await fetchAnimationStatus(animation.value!.id)
      animation.value = updated
      progress.value = updated.progress || 0
      
      if (updated.status === 'completed' || updated.status === 'failed') {
        clearInterval(interval)
        generating.value = false
      }
    }, 2000)
  } catch (error) {
    console.error('生成失败', error)
    generating.value = false
  }
}
</script>
```

---

## 7. 性能优化

### 7.1 数据库优化

1. **查询优化**
   - 使用覆盖索引避免回表
   - 分页查询使用游标而非OFFSET
   - 热门数据Redis缓存

2. **写入优化**
   - 批量插入浏览记录
   - 异步更新热度和评分统计
   - 延迟更新FTS索引

### 7.2 前端优化

1. **列表渲染**
   - 虚拟滚动（IntersectionObserver）
   - 图片懒加载
   - 缩略图CDN加速

2. **状态管理**
   - 本地缓存推荐结果
   - 防抖搜索输入
   - 乐观更新（评分、点赞）

### 7.3 缓存策略

```python
class DiaryCacheService:
    """日记缓存服务"""
    
    CACHE_TTL = {
        'recommendations': 300,  # 5分钟
        'hot_diaries': 600,      # 10分钟
        'detail': 1800,          # 30分钟
    }
    
    async def get_recommendations(
        self,
        filters: DiaryFilters
    ) -> List[Diary]:
        cache_key = f"diary:rec:{hash(filters)}"
        
        # 尝试从缓存读取
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # 查询数据库
        result = await self.service.recommend_diaries(filters)
        
        # 写入缓存
        await self.redis.setex(
            cache_key,
            self.CACHE_TTL['recommendations'],
            json.dumps(result)
        )
        
        return result
```

---

## 8. 测试策略

### 8.1 单元测试

```python
# tests/test_diary_ranking.py
def test_top_k_hybrid_score():
    """测试TopK推荐算法"""
    diaries = generate_test_diaries(100)
    interests = ['自然风光', '历史文化']
    
    result = ranking_algorithm.top_k_by_score(
        diaries, k=10, interests=interests
    )
    
    assert len(result) == 10
    # 验证分数递减
    for i in range(len(result) - 1):
        assert result[i].score >= result[i + 1].score

# tests/test_compression.py
def test_compression_ratio():
    """测试压缩率"""
    content = "Lorem ipsum..." * 100
    compressed = compression_service.compress_content(content)
    
    ratio = len(compressed) / len(content.encode())
    assert ratio < 0.5  # 至少50%压缩率
    
    # 验证可还原
    decompressed = compression_service.decompress_content(compressed)
    assert decompressed == content
```

### 8.2 集成测试

```python
# tests/test_diary_api.py
async def test_create_and_search_diary(client):
    """测试创建日记并全文检索"""
    # 1. 创建日记
    diary_data = {
        'title': '西湖印象',
        'content': '杭州西湖的美景令人难忘...',
        'region_id': 1,
        'tags': ['自然风光', '休闲'],
    }
    response = await client.post('/diaries', json=diary_data)
    assert response.status_code == 200
    diary_id = response.json()['id']
    
    # 2. 全文检索
    response = await client.get('/diaries/search?q=西湖')
    assert response.status_code == 200
    items = response.json()['items']
    assert any(item['id'] == diary_id for item in items)
```

### 8.3 性能测试

```python
# tests/performance/test_top_k_performance.py
import time

def test_top_k_performance():
    """测试TopK算法性能"""
    sizes = [100, 1000, 10000, 100000]
    
    for n in sizes:
        diaries = generate_test_diaries(n)
        
        start = time.time()
        result = ranking_algorithm.top_k_by_score(diaries, k=10)
        elapsed = time.time() - start
        
        print(f"n={n}, time={elapsed:.4f}s")
        assert elapsed < 1.0  # 应在1秒内完成
```

---

## 9. 部署方案

### 9.1 环境变量

```bash
# .env
WAN25_API_KEY=your_api_key
WAN25_API_URL=https://api.wan25.com
REDIS_URL=redis://localhost:6379
CDN_BASE_URL=https://cdn.example.com
```

### 9.2 部署检查清单

- [ ] 数据库索引已创建
- [ ] FTS5虚拟表已初始化
- [ ] Redis缓存已配置
- [ ] CDN已配置图片上传
- [ ] wan2.5 API密钥已配置
- [ ] 后台任务队列已启动（Celery/RQ）
- [ ] 日志监控已配置

---

## 10. 开发计划

### Phase 1: 基础功能（预计3-4天）
- [ ] 数据库模型完善
- [ ] CRUD API实现
- [ ] 基础前端页面
- [ ] 评分系统

### Phase 2: 核心算法（预计2-3天）
- [ ] TopK推荐算法
- [ ] 全文检索
- [ ] 无损压缩

### Phase 3: 高级功能（预计3-4天）
- [ ] AIGC动画生成
- [ ] 性能优化

### Phase 4: 测试与部署（预计2天）
- [ ] 单元测试
- [ ] 集成测试
- [ ] 部署上线

---

## 11. 风险与挑战

### 11.1 技术风险


### 11.2 产品风险


## 12. 参考资料

- [SQLite FTS5文档](https://www.sqlite.org/fts5.html)
- [Python zlib文档](https://docs.python.org/3/library/zlib.html)
- [FastAPI最佳实践](https://fastapi.tiangolo.com/tutorial/)
- [Vue 3组合式API](https://vuejs.org/guide/introduction.html)
- [堆排序算法](https://en.wikipedia.org/wiki/Heapsort)

---

**文档版本**: v1.0  
**最后更新**: 2025年10月3日  
**作者**: GitHub Copilot
