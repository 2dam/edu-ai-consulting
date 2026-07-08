import { NextResponse } from 'next/server'
import { BACKEND_URL } from '@/lib/backend'

// 어린이집·유치원·초등학교 기초자료 (crawler/early_education_spider 수집분).
export async function GET() {
  try {
    const res = await fetch(`${BACKEND_URL}/education-facilities?limit=20000`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(30000),
    })
    if (res.ok) {
      const data = await res.json()
      return NextResponse.json(data)
    }
    console.error('education-facilities backend responded', res.status)
  } catch (err) {
    // 백엔드 미실행/타임아웃 시 빈 목록으로 폴백 — 원인은 로그에 남긴다.
    console.error('education-facilities fetch failed', err)
  }
  return NextResponse.json({ items: [], total: 0, summary_by_type: {} })
}
