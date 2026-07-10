// 학원 평판 관리자 페이지용 간단한 토큰 게이트.
//
// /api/reputation/[...path]/route.ts가 백엔드에는 관리자 헤더를 항상 붙여 보내므로,
// 브라우저 쪽에서 이 토큰이 없으면 프록시가 401로 막는다 — 실제 사용자 계정 시스템이
// 아니라 "URL을 안다고 아무나 들어오지 못하게" 막는 최소한의 장치다.
const STORAGE_KEY = 'eduintel_admin_token'

export function getAdminToken(): string {
  if (typeof window === 'undefined') return ''
  return sessionStorage.getItem(STORAGE_KEY) || ''
}

export function setAdminToken(token: string): void {
  sessionStorage.setItem(STORAGE_KEY, token)
}

export function clearAdminToken(): void {
  sessionStorage.removeItem(STORAGE_KEY)
}

export async function adminFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  headers.set('X-Admin-Token', getAdminToken())
  return fetch(`/api/reputation/${path}`, { ...init, headers })
}
