import request, { type ApiResponse, type PageResult } from './request'

export interface AccessRequest {
  id: number
  user_id: number
  status: string
  reason: string | null
  reviewer_id: number | null
  review_note: string | null
  created_at: string
  reviewed_at: string | null
  username: string | null
  nickname: string | null
}

export function submitAccessRequest(reason?: string) {
  return request.post<any, ApiResponse<AccessRequest>>('/permissions/access-requests', { reason })
}

export function getAccessRequests(params: {
  status?: string
  page?: number
  page_size?: number
}) {
  return request.get<any, ApiResponse<PageResult<AccessRequest>>>('/permissions/access-requests', {
    params,
  })
}

export function reviewAccessRequest(requestId: number, approve: boolean, review_note?: string) {
  return request.post<any, ApiResponse<AccessRequest>>(
    `/permissions/access-requests/${requestId}/review`,
    { approve, review_note }
  )
}

export function revokeLibraryAccess(userId: number) {
  return request.post<any, ApiResponse<{ user_id: number; view_library: boolean }>>(
    `/permissions/users/${userId}/revoke-library`
  )
}

export function getPermissionSettings() {
  return request.get<any, ApiResponse<{ block_upper_role_tasks: boolean }>>('/permissions/settings')
}

export function updatePermissionSettings(block_upper_role_tasks: boolean) {
  return request.put<any, ApiResponse<{ block_upper_role_tasks: boolean }>>(
    '/permissions/settings',
    null,
    { params: { block_upper_role_tasks } }
  )
}
