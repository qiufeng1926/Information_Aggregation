import request, { type ApiResponse, type PageResult } from './request'

export interface ManagedUser {
  id: number
  username: string
  nickname: string | null
  role: string
  status: number
  view_library: boolean
  created_at: string
}

export function getUsers(params: { page?: number; page_size?: number }) {
  return request.get<any, ApiResponse<PageResult<ManagedUser>>>('/users', { params })
}

export function createUser(data: {
  username: string
  password: string
  nickname?: string
  role: string
}) {
  return request.post<any, ApiResponse<ManagedUser>>('/users', data)
}

export function updateUser(
  userId: number,
  data: Partial<{
    nickname: string
    role: string
    status: number
    view_library: boolean
    password: string
  }>
) {
  return request.put<any, ApiResponse<ManagedUser>>(`/users/${userId}`, data)
}

export function deleteUser(userId: number) {
  return request.delete<any, ApiResponse<null>>(`/users/${userId}`)
}
