import request, { type ApiResponse } from './request'

export interface TokenData {
  access_token: string
  token_type: string
}

export interface UserInfo {
  id: number
  username: string
  nickname: string | null
  role: string
}

export function login(username: string, password: string) {
  const form = new URLSearchParams()
  form.append('username', username)
  form.append('password', password)
  return request.post<any, ApiResponse<TokenData>>('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export function getMe() {
  return request.get<any, ApiResponse<UserInfo>>('/auth/me')
}
