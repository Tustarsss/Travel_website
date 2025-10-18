/**
 * TypeScript type definitions for Diary feature
 */

export type DiaryStatus = 'draft' | 'published'

export type DiaryMediaType = 'image' | 'video'

export type DiarySortBy = 'hybrid' | 'popularity' | 'rating' | 'latest'

export interface DiaryMediaPlaceholder {
  placeholder: string
  media_type: DiaryMediaType
  filename: string
  content_type?: string
}

export interface DiaryMediaUpload extends DiaryMediaPlaceholder {
  file: File
}

export interface DiaryMediaItem {
  id: number
  placeholder: string
  filename: string
  content_type: string
  media_type: DiaryMediaType
  url: string
  original_size: number
  compressed_size: number
  is_compressed: boolean
}

/**
 * Simplified user information
 */
export interface DiaryUser {
  id: string
  username: string
  // display_name removed; use username
}

/**
 * Simplified region information
 */
export interface DiaryRegion {
  id: number
  name: string
  type: string
  city?: string
}

/**
 * Diary list item (summary view)
 */
export interface DiaryListItem {
  id: number
  title: string
  content_preview: string
  author: DiaryUser
  region: DiaryRegion
  cover_image?: string
  tags: string[]
  popularity: number
  rating: number
  ratings_count: number
  comments_count: number
  status: DiaryStatus
  created_at: string
  updated_at: string
}

/**
 * Complete diary details
 */
export interface DiaryDetail extends DiaryListItem {
  content: string
  media_urls: string[]
  media_types: DiaryMediaType[]
  media_items: DiaryMediaItem[]
  is_compressed: boolean
}

/**
 * Request to create a new diary
 */
export interface DiaryCreateRequest {
  title: string
  content: string
  region_id: number
  tags?: string[]
  media_placeholders?: DiaryMediaPlaceholder[]
  status?: DiaryStatus
}

/**
 * Request to update a diary
 */
export interface DiaryUpdateRequest {
  title?: string
  content?: string
  region_id?: number
  tags?: string[]
  status?: DiaryStatus
}

/**
 * Response after creating a diary
 */
export interface DiaryCreateResponse {
  id: number
  title: string
  created_at: string
  compressed: boolean
  compression_ratio?: number
}

/**
 * Diary with recommendation score
 */
export interface DiaryRecommendationItem {
  diary: DiaryListItem
  score: number
  interest_matches: string[]
}

/**
 * Diary recommendation response
 */
export interface DiaryRecommendationResponse {
  items: DiaryRecommendationItem[]
  sort_by: string
  generated_at: string
  limit: number
  total_candidates: number
  total: number // Alias for total_candidates for UI consistency
  query?: string | null
  interests: string[]
  execution_time_ms?: number
}

/**
 * Diary list response with pagination
 */
export interface DiaryListResponse {
  items: DiaryListItem[]
  total: number
  page: number
  page_size: number
}

/**
 * Request to rate a diary
 */
export interface DiaryRatingRequest {
  score: number // 1-5
  comment?: string
}

/**
 * Diary rating response
 */
export interface DiaryRatingResponse {
  id: number
  diary_id: number
  user_id: string
  score: number
  comment?: string
  created_at: string
  updated_at: string
}

export interface DiaryRatingUser {
  id: string
  username: string
  // display_name removed; use username
}

export interface DiaryRatingItem extends DiaryRatingResponse {
  user: DiaryRatingUser
}

export interface DiaryRatingListResponse {
  items: DiaryRatingItem[]
  total: number
  page: number
  page_size: number
  average_score: number
  score_distribution: Record<number, number>
  comments_count: number
  current_user_rating?: DiaryRatingItem
}

/**
 * AIGC animation generation request
 */
export interface AnimationGenerateRequest {
  style?: string
  duration?: number
  custom_description?: string
}

/**
 * Diary animation response
 */
export interface DiaryAnimation {
  id: number
  diary_id: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  video_url?: string
  thumbnail_url?: string
  error_message?: string
  created_at: string
}

/**
 * Query parameters for diary list
 */
export interface DiaryListParams {
  page?: number
  page_size?: number
  region_id?: number
  author_id?: string
  status?: DiaryStatus
  interests?: string[]
  q?: string
}

/**
 * Query parameters for diary recommendations
 */
export interface DiaryRecommendationParams {
  limit?: number
  sort_by?: DiarySortBy
  interests?: string[]
  region_id?: number
}
