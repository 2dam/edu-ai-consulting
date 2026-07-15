import { NextRequest, NextResponse } from 'next/server'
import { BACKEND_URL } from '@/lib/backend'

// 학원 평판 API 전체를 한 파일에서 프록시한다 (committee/run/route.ts와 같은 포워딩 패턴을
// 일반화). 관리 엔드포인트는 백엔드의 임시 인증(X-User-Id 헤더 + require_admin)에 맞춰
// 고정 관리자 id를 실어 보낸다.
const ADMIN_USER_ID = process.env.ADMIN_USER_ID ?? '1'

type Ctx = { params: Promise<{ path: string[] }> }

async function forward(request: NextRequest, path: string[]) {
  const search = new URL(request.url).search
  const target = `${BACKEND_URL}/reputation/${path.join('/')}${search}`

  const headers: Record<string, string> = { 'X-User-Id': ADMIN_USER_ID }
  let body: BodyInit | undefined

  if (!['GET', 'HEAD'].includes(request.method)) {
    const contentType = request.headers.get('content-type') || ''
    if (contentType.includes('multipart/form-data')) {
      // fetch가 FormData를 boundary 포함 Content-Type으로 알아서 직렬화하므로 직접 지정하지 않는다.
      body = await request.formData()
    } else {
      const text = await request.text()
      if (text) {
        headers['Content-Type'] = contentType || 'application/json'
        body = text
      }
    }
  }

  try {
    const res = await fetch(target, {
      method: request.method,
      headers,
      body,
      signal: AbortSignal.timeout(30000),
    })
    const buf = await res.arrayBuffer()
    const outHeaders: Record<string, string> = {
      'Content-Type': res.headers.get('content-type') || 'application/octet-stream',
    }
    const disposition = res.headers.get('content-disposition')
    if (disposition) outHeaders['Content-Disposition'] = disposition
    return new NextResponse(buf, { status: res.status, headers: outHeaders })
  } catch {
    return NextResponse.json({ detail: '백엔드 연결 실패 또는 시간 초과 (학원 평판 API)' }, { status: 502 })
  }
}

export async function GET(request: NextRequest, ctx: Ctx) {
  return forward(request, (await ctx.params).path)
}
export async function POST(request: NextRequest, ctx: Ctx) {
  return forward(request, (await ctx.params).path)
}
export async function PATCH(request: NextRequest, ctx: Ctx) {
  return forward(request, (await ctx.params).path)
}
export async function DELETE(request: NextRequest, ctx: Ctx) {
  return forward(request, (await ctx.params).path)
}
