import { NextResponse } from 'next/server'
import { BACKEND_URL } from '@/lib/backend'

export async function POST(request: Request) {
  const body = await request.json().catch(() => null)
  const draft = body?.draft
  const feedback = body?.feedback
  if (typeof draft !== 'string' || typeof feedback !== 'string' || !feedback.trim()) {
    return NextResponse.json({ detail: '피드백을 입력하세요' }, { status: 400 })
  }

  try {
    const res = await fetch(`${BACKEND_URL}/committee/revise`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ draft, feedback }),
      signal: AbortSignal.timeout(60_000),
    })
    const data = await res.json().catch(() => ({ detail: '응답을 해석할 수 없습니다' }))
    return NextResponse.json(data, { status: res.status })
  } catch {
    return NextResponse.json({ detail: '최종안 생성 중 오류가 발생했습니다 (백엔드 연결 실패 또는 시간 초과)' }, { status: 502 })
  }
}
