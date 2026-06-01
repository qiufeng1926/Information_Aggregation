import request, { type ApiResponse, type PageResult } from './request'

export interface CollectionFilters {
  follower_min?: number
  follower_max?: number
  avg_views_min?: number
  limit?: number
}

export interface CollectionTask {
  id: number
  user_id: number
  title: string | null
  platform: string
  keyword: string
  filters: CollectionFilters | null
  status: string
  result_count: number
  approved_count: number
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface CollectedInfluencer {
  id: number
  task_id: number
  platform: string
  platform_uid: string
  nickname: string | null
  avatar_url: string | null
  profile_url: string | null
  follower_count: number
  engagement_rate: number | null
  avg_views: number | null
  source: string | null
  matched_tags: string[] | null
  match_score: number | null
  extra_data: Record<string, unknown> | null
  review_status: string
  influencer_id: number | null
  created_at: string
}

export interface ReviewResult {
  approved: number
  rejected: number
  skipped: number
}

export function createCollectionTask(data: {
  platform: string
  keyword: string
  title?: string
  filters?: CollectionFilters
}) {
  return request.post<any, ApiResponse<CollectionTask>>('/collection/tasks', data)
}

export function getCollectionTasks(params: { page?: number; page_size?: number }) {
  return request.get<any, ApiResponse<PageResult<CollectionTask>>>('/collection/tasks', { params })
}

export function retryCollectionTask(taskId: number) {
  return request.post<any, ApiResponse<CollectionTask>>(`/collection/tasks/${taskId}/retry`)
}

export function getPendingReview(params: {
  task_id?: number
  page?: number
  page_size?: number
}) {
  return request.get<any, ApiResponse<PageResult<CollectedInfluencer>>>('/collection/pending', { params })
}

export function approveCollected(ids: number[]) {
  return request.post<any, ApiResponse<ReviewResult>>('/collection/approve', { ids })
}

export function rejectCollected(ids: number[]) {
  return request.post<any, ApiResponse<ReviewResult>>('/collection/reject', { ids })
}

export const TASK_STATUS_MAP: Record<string, { label: string; type: string }> = {
  pending: { label: '等待中', type: 'info' },
  running: { label: '采集中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
}

export const PLATFORM_OPTIONS = [
  { label: '抖音', value: 'douyin' },
  { label: '小红书', value: 'xiaohongshu' },
  { label: '快手', value: 'kuaishou' },
]

export function formatPlatform(value: string) {
  return PLATFORM_OPTIONS.find((p) => p.value === value)?.label || value
}

export function formatFollowers(count: number) {
  if (count >= 10000) return `${(count / 10000).toFixed(1)}万`
  return count.toString()
}
