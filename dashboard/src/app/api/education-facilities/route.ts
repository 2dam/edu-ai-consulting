import { NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'

// 어린이집·유치원·초등학교 기초자료 (crawler/early_education_spider 수집분).
export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/education-facilities?limit=20000`, {
      next: { revalidate: 60 },
      signal: AbortSignal.timeout(8000),
    })
    if (res.ok) {
      const data = await res.json()
      return NextResponse.json(data)
    }
  } catch {
    // 백엔드 미실행 시 빈 목록
  }
  return NextResponse.json({ items: [], total: 0, summary_by_type: {} })
}
