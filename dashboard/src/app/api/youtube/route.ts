import { NextResponse } from 'next/server'
import { BACKEND_URL } from '@/lib/backend'

// 실시간 교육 동영상 — 검색어에 맞는 최신 영상 1건 (YouTube Data API, FastAPI 백엔드 경유).
export async function GET(request: Request) {
  const q = new URL(request.url).searchParams.get('q') || ''
  try {
    const res = await fetch(`${BACKEND_URL}/youtube-video?q=${encodeURIComponent(q)}`, {
      next: { revalidate: 300 },
      signal: AbortSignal.timeout(8000),
    })
    if (res.ok) {
      const data = await res.json()
      return NextResponse.json(data)
    }
  } catch {
    // 백엔드 미실행 또는 YOUTUBE_API_KEY 미설정 시 결과 없음
  }
  return NextResponse.json({ result: null })
}
