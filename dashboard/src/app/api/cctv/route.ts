import { NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'

// 전국 공공 도로 CCTV (국가교통정보센터 ITS) — FastAPI 백엔드가 키를 감춘 채 프록시.
export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/cctv`, { next: { revalidate: 60 }, signal: AbortSignal.timeout(8000) })
    if (res.ok) {
      const data = await res.json()
      return NextResponse.json(data)
    }
  } catch {
    // 백엔드 미실행 또는 ITS_API_KEY 미설정 시 빈 목록
  }
  return NextResponse.json({ items: [], total: 0, source: '국가교통정보센터(ITS) 공공 도로 CCTV' })
}
